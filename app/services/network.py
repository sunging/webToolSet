"""Network diagnostic services."""

import json
import ipaddress
import logging
import re
import socket
import ssl
import statistics
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import dns.exception
import dns.rdatatype
import dns.resolver
import dns.reversename
import httpx
import icmplib
from cryptography import x509
from cryptography.x509.oid import NameOID
from wakeonlan import send_magic_packet

logger = logging.getLogger(__name__)

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_X509_NAME_LABELS = {
    NameOID.COMMON_NAME: "commonName",
    NameOID.ORGANIZATION_NAME: "organizationName",
    NameOID.ORGANIZATIONAL_UNIT_NAME: "organizationalUnitName",
    NameOID.COUNTRY_NAME: "countryName",
    NameOID.STATE_OR_PROVINCE_NAME: "stateOrProvinceName",
    NameOID.LOCALITY_NAME: "localityName",
    NameOID.EMAIL_ADDRESS: "emailAddress",
}
DEFAULT_DNS_RESOLVERS = [
    {"name": "System", "servers": None},
    {"name": "Cloudflare", "servers": ["1.1.1.1"]},
    {"name": "Google", "servers": ["8.8.8.8"]},
    {"name": "Quad9", "servers": ["9.9.9.9"]},
]
SECURITY_HEADERS = [
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
]
CACHE_HEADERS = ["cache-control", "expires", "etag", "last-modified", "age"]


def _normalize_url(url: str) -> str:
    """Return a URL with an explicit scheme."""
    url = url.strip()
    if not url:
        return url
    parsed = urlparse(url)
    if not parsed.scheme:
        return f"https://{url}"
    return url


def _headers_dict(headers) -> dict[str, str]:
    """Convert HTTP headers to a plain dict."""
    return {key: value for key, value in headers.items()}


def _selected_headers(headers, names: list[str]) -> dict[str, str]:
    """Return selected headers using case-insensitive matching."""
    lower_headers = {key.lower(): value for key, value in headers.items()}
    return {name: lower_headers[name] for name in names if name in lower_headers}


def _redirect_history(response: httpx.Response) -> list[dict]:
    """Build a compact redirect history."""
    return [
        {
            "status_code": item.status_code,
            "url": str(item.url),
            "location": item.headers.get("location"),
        }
        for item in response.history
    ]


def _read_capped(response: httpx.Response, limit: int) -> tuple[bytes, bool]:
    """Read a streamed response body up to ``limit`` bytes.

    Returns the (possibly truncated) content and whether truncation occurred.
    """
    content = bytearray()
    for chunk in response.iter_bytes():
        content.extend(chunk)
        if len(content) > limit:
            return bytes(content[:limit]), True
    return bytes(content), False


def _resolve_dns_records(
    resolver: dns.resolver.Resolver, name: str, record_type: str
) -> tuple[list[dict], int | None, str | None]:
    """Resolve DNS records, returning (records, ttl, error)."""
    try:
        answers = resolver.resolve(name, record_type)
    except dns.resolver.NXDOMAIN:
        return [], None, f"Name does not exist: {name}"
    except dns.resolver.NoAnswer:
        return [], None, f"No {record_type} records found for {name}"
    except dns.resolver.NoNameservers:
        return [], None, "No nameservers could answer the query"
    except dns.exception.Timeout:
        return [], None, "DNS query timed out"
    except dns.rdatatype.UnknownRdatatype:
        return [], None, f"Unknown record type: {record_type}"
    except Exception as e:
        logger.debug(f"dns query error: {e}")
        return [], None, f"DNS query failed: {e}"

    ttl = answers.rrset.ttl if answers.rrset is not None else None
    records = [
        {"type": record_type, "value": str(rdata), "ttl": ttl}
        for rdata in answers
    ]
    return records, ttl, None


def _x509_name_dict(name: x509.Name) -> dict[str, str]:
    """Convert an x509 Name to a label->value dict (last value wins)."""
    result: dict[str, str] = {}
    for attr in name:
        label = _X509_NAME_LABELS.get(attr.oid, attr.oid.dotted_string)
        result[label] = str(attr.value)
    return result


def _x509_san(cert: x509.Certificate) -> list[str]:
    """Return DNS subject alternative names from a certificate."""
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
    except x509.ExtensionNotFound:
        return []
    return ext.value.get_values_for_type(x509.DNSName)


def _stddev(values: list[float]) -> float:
    """Return population standard deviation rounded for API output."""
    if len(values) < 2:
        return 0.0
    return round(statistics.pstdev(values), 3)


def _ping_result(address: str, host) -> dict:
    """Convert an icmplib Host into the enhanced ping response shape."""
    rtts = [round(value, 3) for value in host.rtts]
    probes = [
        {
            "sequence": index + 1,
            "rtt": rtt,
            "success": True,
            "error": None,
        }
        for index, rtt in enumerate(rtts)
    ]
    for index in range(len(probes), host.packets_sent):
        probes.append(
            {
                "sequence": index + 1,
                "rtt": None,
                "success": False,
                "error": "Request timed out",
            }
        )

    return {
        "address": address,
        "resolved_address": host.address,
        "delay": host.avg_rtt if host.is_alive else None,
        "sent": host.packets_sent,
        "received": host.packets_received,
        "packet_loss": round(host.packet_loss * 100, 2),
        "min_rtt": host.min_rtt if host.is_alive else None,
        "avg_rtt": host.avg_rtt if host.is_alive else None,
        "max_rtt": host.max_rtt if host.is_alive else None,
        "jitter": host.jitter if host.is_alive else None,
        "stddev": _stddev(rtts) if host.is_alive else None,
        "probes": probes,
    }


class PingService:
    """Service for ICMP ping operations."""

    @staticmethod
    def ping(
        address: str, count: int = 4, timeout: int = 2, interval: float = 0.2
    ) -> tuple[dict | None, str | None]:
        """
        Perform ICMP ping to the specified address.

        Args:
            address: The target IP address or hostname.

        Returns:
            A tuple of (result, error_message). result contains latency statistics.

        """
        try:
            host = icmplib.ping(address, count=count, timeout=timeout, interval=interval)
        except icmplib.NameLookupError as e:
            return None, f"Name lookup failed: {e}"
        except icmplib.SocketPermissionError as e:
            return None, f"Permission denied (raw socket requires privileges): {e}"
        except Exception as e:
            return None, f"Ping failed: {e}"

        return _ping_result(address, host), None


class HttpCheckService:
    """Service for HTTP/HTTPS checks."""

    @staticmethod
    def check(url: str, timeout: int = 5) -> tuple[dict | None, str | None]:
        """
        Fetch a URL and return status, timing, redirects and useful headers.

        Args:
            url: URL to fetch. Defaults to HTTPS when no scheme is supplied.
            timeout: Request timeout in seconds.

        Returns:
            A tuple of (result, error_message).

        """
        url = _normalize_url(url)
        if not url:
            return None, "Empty URL"
        if urlparse(url).scheme not in {"http", "https"}:
            return None, "Unsupported URL scheme"

        try:
            start = time.monotonic()
            with httpx.Client(
                timeout=timeout,
                follow_redirects=True,
                max_redirects=5,
            ) as client:
                with client.stream("GET", url) as response:
                    content, _truncated = _read_capped(response, MAX_RESPONSE_BYTES)
            elapsed = round((time.monotonic() - start) * 1000, 2)
        except httpx.InvalidURL as e:
            return None, f"Invalid URL: {e}"
        except httpx.TooManyRedirects:
            return None, "Too many redirects"
        except httpx.TimeoutException:
            return None, "HTTP request timed out"
        except httpx.RequestError as e:
            return None, f"HTTP request failed: {e}"

        headers = _headers_dict(response.headers)
        return {
            "url": url,
            "final_url": str(response.url),
            "status_code": response.status_code,
            "reason_phrase": response.reason_phrase,
            "elapsed_ms": elapsed,
            "redirects": _redirect_history(response),
            "response_size": len(content),
            "content_type": response.headers.get("content-type"),
            "server": response.headers.get("server"),
            "headers": headers,
            "security_headers": _selected_headers(headers, SECURITY_HEADERS),
            "cache_headers": _selected_headers(headers, CACHE_HEADERS),
        }, None


class RequestInspectorService:
    """Service for request/response header inspection."""

    ALLOWED_METHODS = {"GET", "HEAD", "POST"}
    MAX_BODY_BYTES = 16 * 1024
    RESPONSE_PREVIEW_BYTES = 4 * 1024

    @staticmethod
    def _parse_headers(headers: str | None) -> tuple[dict[str, str] | None, str | None]:
        """Parse optional request headers from a JSON object string."""
        if not headers:
            return {}, None
        try:
            parsed_headers = json.loads(headers)
        except json.JSONDecodeError as e:
            return None, f"Invalid headers JSON: {e}"
        if not isinstance(parsed_headers, dict):
            return None, "Headers must be a JSON object"
        return {str(key): str(value) for key, value in parsed_headers.items()}, None

    @staticmethod
    def _body_bytes(method: str, body: str | None) -> tuple[bytes | None, str | None]:
        """Validate and encode the optional request body."""
        request_body = body or ""
        body_bytes = request_body.encode("utf-8")
        if len(body_bytes) > RequestInspectorService.MAX_BODY_BYTES:
            return None, "Request body exceeds 16 KB limit"
        if method != "POST" and request_body:
            return None, "Request body is only supported for POST"
        return body_bytes, None

    @staticmethod
    def _request_summary(
        method: str, url: str, headers: dict[str, str], body_bytes: bytes
    ) -> dict:
        """Build the response request summary."""
        return {
            "method": method,
            "url": url,
            "headers": headers,
            "body_size": len(body_bytes),
        }

    @staticmethod
    def _response_summary(
        response: httpx.Response, content: bytes, capped: bool, elapsed: float
    ) -> dict:
        """Build the response metadata summary."""
        response_headers = _headers_dict(response.headers)
        preview = content[: RequestInspectorService.RESPONSE_PREVIEW_BYTES].decode(
            response.encoding or "utf-8", "replace"
        )
        return {
            "status_code": response.status_code,
            "reason_phrase": response.reason_phrase,
            "final_url": str(response.url),
            "elapsed_ms": elapsed,
            "headers": response_headers,
            "content_type": response.headers.get("content-type"),
            "server": response.headers.get("server"),
            "body_size": len(content),
            "body_preview": preview,
            "truncated": capped
            or len(content) > RequestInspectorService.RESPONSE_PREVIEW_BYTES,
            "security_headers": _selected_headers(response_headers, SECURITY_HEADERS),
            "cache_headers": _selected_headers(response_headers, CACHE_HEADERS),
        }

    @staticmethod
    def inspect(
        url: str,
        method: str = "GET",
        headers: str | None = None,
        body: str | None = None,
        timeout: int = 5,
    ) -> tuple[dict | None, str | None]:
        """
        Send a controlled HTTP request and return request/response metadata.

        Args:
            url: URL to inspect.
            method: GET, HEAD or POST.
            headers: Optional JSON object containing request headers.
            body: Optional body for POST requests.
            timeout: Request timeout in seconds.

        Returns:
            A tuple of (result, error_message).

        """
        url = _normalize_url(url)
        method = method.upper()
        if method not in RequestInspectorService.ALLOWED_METHODS:
            return None, f"Unsupported method: {method}"
        if urlparse(url).scheme not in {"http", "https"}:
            return None, "Unsupported URL scheme"

        request_headers, error = RequestInspectorService._parse_headers(headers)
        if error:
            return None, error
        body_bytes, error = RequestInspectorService._body_bytes(method, body)
        if error:
            return None, error

        try:
            start = time.monotonic()
            with httpx.Client(
                timeout=timeout,
                follow_redirects=True,
                max_redirects=5,
            ) as client:
                with client.stream(
                    method,
                    url,
                    headers=request_headers,
                    content=body_bytes if method == "POST" else None,
                ) as response:
                    content, capped = _read_capped(response, MAX_RESPONSE_BYTES)
            elapsed = round((time.monotonic() - start) * 1000, 2)
        except httpx.InvalidURL as e:
            return None, f"Invalid URL: {e}"
        except httpx.TooManyRedirects:
            return None, "Too many redirects"
        except httpx.TimeoutException:
            return None, "HTTP request timed out"
        except httpx.RequestError as e:
            return None, f"HTTP request failed: {e}"

        return {
            "request": RequestInspectorService._request_summary(
                method, url, request_headers or {}, body_bytes or b""
            ),
            "response": RequestInspectorService._response_summary(
                response, content, capped, elapsed
            ),
            "redirects": _redirect_history(response),
        }, None


class TlsCheckService:
    """Service for TLS certificate checks."""

    @staticmethod
    def check(host: str, port: int = 443, timeout: int = 5) -> tuple[dict | None, str | None]:
        """
        Inspect a server TLS certificate and negotiated protocol.

        Args:
            host: Server hostname.
            port: TLS port.
            timeout: Connection timeout in seconds.

        Returns:
            A tuple of (result, error_message).

        """
        host = host.strip()
        if not host:
            return None, "Empty host"

        # Disable verification so we can still inspect expired, self-signed or
        # hostname-mismatched certificates -- which is exactly what this tool
        # exists to report. A verifying context would abort the handshake first.
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=host) as tls_sock:
                    der_cert = tls_sock.getpeercert(binary_form=True)
                    protocol = tls_sock.version()
                    cipher = tls_sock.cipher()
        except socket.gaierror as e:
            return None, f"Name resolution failed: {e}"
        except ssl.SSLError as e:
            return None, f"TLS handshake failed: {e}"
        except (socket.timeout, TimeoutError):
            return None, "TLS connection timed out"
        except OSError as e:
            return None, f"TLS connection failed: {e}"

        if not der_cert:
            return None, "No certificate presented by server"

        cert = x509.load_der_x509_certificate(der_cert)
        starts_at = cert.not_valid_before_utc
        expires_at = cert.not_valid_after_utc
        now = datetime.now(timezone.utc)

        return {
            "host": host,
            "port": port,
            "subject": _x509_name_dict(cert.subject),
            "issuer": _x509_name_dict(cert.issuer),
            "subject_alt_names": _x509_san(cert),
            "not_before": starts_at.isoformat(),
            "not_after": expires_at.isoformat(),
            "days_remaining": (expires_at - now).days,
            "expired": now > expires_at,
            "protocol": protocol,
            "cipher": cipher[0] if cipher else None,
        }, None


class DnsCompareService:
    """Service for comparing DNS answers across resolvers."""

    @staticmethod
    def compare(
        name: str, record_type: str = "A", timeout: int = 5
    ) -> tuple[dict | None, str | None]:
        """
        Query multiple recursive resolvers for the same record.

        Args:
            name: DNS name.
            record_type: DNS record type.
            timeout: Per-resolver timeout in seconds.

        Returns:
            A tuple of (result, error_message).

        """
        record_type = record_type.upper()

        results = []
        for resolver_config in DEFAULT_DNS_RESOLVERS:
            resolver = dns.resolver.Resolver()
            resolver.timeout = timeout
            resolver.lifetime = timeout
            servers = resolver_config["servers"]
            if servers:
                resolver.nameservers = servers

            start = time.monotonic()
            records, ttl, error = _resolve_dns_records(resolver, name, record_type)

            results.append(
                {
                    "resolver": resolver_config["name"],
                    "servers": resolver.nameservers,
                    "records": records,
                    "ttl": ttl,
                    "query_time": round((time.monotonic() - start) * 1000, 2),
                    "error": error,
                }
            )

        return {"name": name, "record_type": record_type, "results": results}, None


class MtrService:
    """Service for MTR-style route quality analysis."""

    @staticmethod
    def _collect_hop_stats(
        address: str, cycles: int, max_hops: int, timeout: int
    ) -> dict[int, dict]:
        """Collect raw hop statistics across traceroute cycles."""
        hop_stats: dict[int, dict] = {}
        for _ in range(cycles):
            hops = icmplib.traceroute(address, max_hops=max_hops, timeout=timeout)
            replies: dict[int, object] = {}
            max_distance = 0
            for hop in hops:
                max_distance = max(max_distance, hop.distance)
                if hop.is_alive:
                    replies[hop.distance] = hop

            # Each cycle probes every TTL up to the furthest hop observed, so
            # count one probe sent per distance even when no reply came back.
            for distance in range(1, max_distance + 1):
                stats = hop_stats.setdefault(
                    distance,
                    {"distance": distance, "addresses": {}, "sent": 0, "rtts": []},
                )
                stats["sent"] += 1
                hop = replies.get(distance)
                if hop is not None:
                    stats["addresses"][hop.address] = (
                        stats["addresses"].get(hop.address, 0) + 1
                    )
                    if hop.avg_rtt is not None:
                        stats["rtts"].append(hop.avg_rtt)
        return hop_stats

    @staticmethod
    def _build_hop_result(distance: int, stats: dict) -> dict:
        """Build one aggregated MTR hop result."""
        rtts = [round(value, 3) for value in stats["rtts"]]
        received = len(rtts)
        sent = stats["sent"]
        loss = round((1 - received / sent) * 100, 2) if sent else 0.0
        address_counts = stats["addresses"]
        best_address = max(address_counts, key=address_counts.get) if address_counts else None
        return {
            "distance": distance,
            "address": best_address,
            "sent": sent,
            "received": received,
            "packet_loss": loss,
            "best_rtt": min(rtts) if rtts else None,
            "avg_rtt": round(sum(rtts) / received, 3) if rtts else None,
            "worst_rtt": max(rtts) if rtts else None,
            "jitter": _stddev(rtts) if rtts else None,
            "addresses": address_counts,
        }

    @staticmethod
    def _quality_summary(hops: list[dict]) -> str:
        """Return a compact route quality summary."""
        worst_loss = max((hop["packet_loss"] for hop in hops), default=0.0)
        reachable = any(hop["received"] > 0 for hop in hops)
        if not reachable:
            return "unreachable"
        if worst_loss >= 50:
            return "poor"
        if worst_loss > 0:
            return "degraded"
        return "good"

    @staticmethod
    def analyze(
        address: str, cycles: int = 5, max_hops: int = 30, timeout: int = 2
    ) -> tuple[dict | None, str | None]:
        """
        Run multiple traceroute cycles and aggregate route quality by hop.

        Args:
            address: Target host.
            cycles: Number of traceroute cycles.
            max_hops: Maximum hop count.
            timeout: Per-hop timeout.

        Returns:
            A tuple of (result, error_message).

        """
        try:
            hop_stats = MtrService._collect_hop_stats(
                address, cycles=cycles, max_hops=max_hops, timeout=timeout
            )
        except icmplib.NameLookupError as e:
            return None, f"Name lookup failed: {e}"
        except icmplib.SocketPermissionError as e:
            return None, f"Permission denied (raw socket requires privileges): {e}"
        except Exception as e:
            logger.debug(f"mtr error: {e}")
            return None, f"MTR failed: {e}"

        hops_result = [
            MtrService._build_hop_result(distance, hop_stats[distance])
            for distance in sorted(hop_stats)
        ]

        return {
            "address": address,
            "cycles": cycles,
            "max_hops": max_hops,
            "hops": hops_result,
            "summary": MtrService._quality_summary(hops_result),
        }, None


class TcpPingService:
    """Service for TCP ping operations."""

    @staticmethod
    def tcping(
        address: str, port: int = 80, timeout: int = 2, count: int = 4
    ) -> tuple[float | None, str | None]:
        """
        Perform TCP ping to the specified address and port.

        Args:
            address: The target IP address or hostname.
            port: The target port number.
            timeout: Connection timeout in seconds.
            count: Number of ping attempts.

        Returns:
            A tuple of (delay_ms, error_message). delay_ms is None if tcping failed.

        """
        conn_times = []

        for _ in range(count):
            sock = socket.socket(
                socket.AF_INET6 if ":" in address else socket.AF_INET,
                socket.SOCK_STREAM,
            )
            sock.settimeout(timeout)
            try:
                start = time.time()
                sock.connect((address, port))
                sock.shutdown(socket.SHUT_RD)
                end = time.time()
                conn_times.append(end - start)
            except socket.timeout:
                conn_times.append(0.0)
            except OSError as e:
                conn_times.append(0.0)
                logger.debug(f"TCP connection error: {e}")
            finally:
                sock.close()

        logger.debug(f"TCPing {address}:{port} {count} times: {conn_times}")

        successful_delays = [d for d in conn_times if d > 0]
        if not successful_delays:
            return None, "All TCP ping attempts failed"

        avg_delay = sum(successful_delays) / len(successful_delays)
        return avg_delay, None


class DnsService:
    """Service for DNS lookup operations (nslookup and dig)."""

    @staticmethod
    def _is_ip_address(name: str) -> bool:
        """Return whether a value is an IP address."""
        try:
            ipaddress.ip_address(name)
        except ValueError:
            return False
        return True

    @staticmethod
    def _reverse_lookup(resolver: dns.resolver.Resolver, name: str) -> list[str]:
        """Resolve PTR records for an IP address."""
        rev_name = dns.reversename.from_address(name)
        answers = resolver.resolve(rev_name, "PTR")
        return [str(r).rstrip(".") for r in answers]

    @staticmethod
    def _forward_lookup(
        resolver: dns.resolver.Resolver, name: str
    ) -> tuple[list[str], str | None]:
        """Resolve A/AAAA records for a hostname."""
        addresses: list[str] = []
        canonical_name: str | None = None
        for rtype in ("A", "AAAA"):
            try:
                answers = resolver.resolve(name, rtype)
            except dns.resolver.NoAnswer:
                continue
            cname = str(answers.canonical_name).rstrip(".")
            if cname and cname != name.rstrip("."):
                canonical_name = cname
            addresses.extend(str(r) for r in answers)
        return addresses, canonical_name

    @staticmethod
    def nslookup(name: str) -> tuple[dict | None, str | None]:
        """
        Perform an nslookup-style DNS resolution.

        Resolves a hostname to its A/AAAA addresses, or performs a reverse
        (PTR) lookup when given an IP address.

        Args:
            name: The hostname or IP address to look up.

        Returns:
            A tuple of (result, error_message). result is a dict with keys
            ``server``, ``addresses`` and ``canonical_name`` when successful.

        """
        resolver = dns.resolver.Resolver()
        server = resolver.nameservers[0] if resolver.nameservers else None

        addresses: list[str] = []
        canonical_name: str | None = None

        try:
            if DnsService._is_ip_address(name):
                addresses = DnsService._reverse_lookup(resolver, name)
            else:
                addresses, canonical_name = DnsService._forward_lookup(resolver, name)
                if not addresses:
                    return None, f"No DNS records found for {name}"
        except dns.resolver.NXDOMAIN:
            return None, f"Name does not exist: {name}"
        except dns.resolver.NoNameservers:
            return None, "No nameservers could answer the query"
        except dns.exception.Timeout:
            return None, "DNS query timed out"
        except Exception as e:
            logger.debug(f"nslookup error: {e}")
            return None, f"DNS lookup failed: {e}"

        return {
            "server": server,
            "addresses": addresses,
            "canonical_name": canonical_name,
        }, None

    @staticmethod
    def dig(name: str, record_type: str = "A") -> tuple[dict | None, str | None]:
        """
        Perform a dig-style DNS query for a specific record type.

        Args:
            name: The domain name to query.
            record_type: DNS record type (e.g. A, AAAA, MX, NS, TXT, CNAME).

        Returns:
            A tuple of (result, error_message). result is a dict with keys
            ``server``, ``records`` and ``query_time`` when successful.

        """
        record_type = record_type.upper()
        resolver = dns.resolver.Resolver()
        server = resolver.nameservers[0] if resolver.nameservers else None

        start = time.time()
        records, _ttl, error = _resolve_dns_records(resolver, name, record_type)
        query_time = (time.time() - start) * 1000
        if error:
            return None, error

        return {
            "server": server,
            "records": records,
            "query_time": query_time,
        }, None


class ReverseIpService:
    """Service for reverse IP (PTR) lookups."""

    @staticmethod
    def reverse(address: str) -> tuple[dict | None, str | None]:
        """
        Perform a reverse DNS (PTR) lookup for an IP address.

        Resolves an IPv4 or IPv6 address to the hostname(s) registered in its
        PTR record(s).

        Args:
            address: The IP address to look up.

        Returns:
            A tuple of (result, error_message). result is a dict with keys
            ``server`` and ``hostnames`` when successful.

        """
        address = address.strip()

        try:
            ipaddress.ip_address(address)
        except ValueError:
            return None, f"Invalid IP address: {address}"

        resolver = dns.resolver.Resolver()
        server = resolver.nameservers[0] if resolver.nameservers else None

        try:
            rev_name = dns.reversename.from_address(address)
            answers = resolver.resolve(rev_name, "PTR")
            hostnames = [str(r).rstrip(".") for r in answers]
        except dns.resolver.NXDOMAIN:
            return None, f"No PTR record found for {address}"
        except dns.resolver.NoAnswer:
            return None, f"No PTR record found for {address}"
        except dns.resolver.NoNameservers:
            return None, "No nameservers could answer the query"
        except dns.exception.Timeout:
            return None, "DNS query timed out"
        except Exception as e:
            logger.debug(f"reverse lookup error: {e}")
            return None, f"Reverse lookup failed: {e}"

        if not hostnames:
            return None, f"No PTR record found for {address}"

        return {"server": server, "hostnames": hostnames}, None


class TracerouteService:
    """Service for traceroute operations."""

    @staticmethod
    def traceroute(
        address: str, max_hops: int = 30, timeout: int = 2
    ) -> tuple[list | None, str | None]:
        """
        Perform a traceroute to the specified address.

        Args:
            address: The target IP address or hostname.
            max_hops: Maximum number of hops to probe.
            timeout: Per-hop timeout in seconds.

        Returns:
            A tuple of (hops, error_message). hops is a list of dicts with
            keys ``distance``, ``address``, ``avg_rtt`` and ``is_alive``.

        """
        try:
            hops = icmplib.traceroute(address, max_hops=max_hops, timeout=timeout)
        except icmplib.NameLookupError as e:
            return None, f"Name lookup failed: {e}"
        except icmplib.SocketPermissionError as e:
            return None, f"Permission denied (raw socket requires privileges): {e}"
        except Exception as e:
            logger.debug(f"traceroute error: {e}")
            return None, f"Traceroute failed: {e}"

        result = [
            {
                "distance": hop.distance,
                "address": hop.address,
                "avg_rtt": hop.avg_rtt,
                "is_alive": hop.is_alive,
            }
            for hop in hops
        ]
        return result, None


class WhoisService:
    """Service for WHOIS lookups (registration info for domains and IPs)."""

    IANA_SERVER = "whois.iana.org"
    WHOIS_PORT = 43
    MAX_REFERRALS = 3
    _REFERRAL_PATTERN = re.compile(
        r"^\s*(?:refer|whois|Registrar WHOIS Server|ReferralServer)\s*:\s*"
        r"(?:whois://)?([A-Za-z0-9.\-]+)",
        re.IGNORECASE | re.MULTILINE,
    )

    @staticmethod
    def _query(server: str, query: str, timeout: int) -> str:
        """Send a single WHOIS query to a server and return the raw response."""
        with socket.create_connection((server, WhoisService.WHOIS_PORT), timeout) as s:
            s.settimeout(timeout)
            s.sendall((query + "\r\n").encode("utf-8"))
            chunks = []
            while True:
                data = s.recv(4096)
                if not data:
                    break
                chunks.append(data)
        return b"".join(chunks).decode("utf-8", "replace")

    @staticmethod
    def whois(
        query: str, timeout: int = 10
    ) -> tuple[dict | None, str | None]:
        """
        Perform a WHOIS lookup, following referrals to the authoritative server.

        Args:
            query: The domain name or IP address to look up.
            timeout: Per-connection timeout in seconds.

        Returns:
            A tuple of (result, error_message). result is a dict with keys
            ``server`` (the last server queried) and ``raw`` (the full text).

        """
        query = query.strip()
        if not query:
            return None, "Empty query"

        server = WhoisService.IANA_SERVER
        seen = {server}
        raw = ""

        try:
            for _ in range(WhoisService.MAX_REFERRALS + 1):
                raw = WhoisService._query(server, query, timeout)

                match = WhoisService._REFERRAL_PATTERN.search(raw)
                if not match:
                    break
                referral = match.group(1).lower()
                if referral in seen:
                    break
                seen.add(referral)
                server = referral
        except socket.gaierror as e:
            return None, f"WHOIS server lookup failed: {e}"
        except (socket.timeout, TimeoutError):
            return None, "WHOIS query timed out"
        except OSError as e:
            logger.debug(f"whois error: {e}")
            return None, f"WHOIS query failed: {e}"

        if not raw.strip():
            return None, f"No WHOIS data found for {query}"

        return {"server": server, "raw": raw}, None


class PortCheckService:
    """Service for TCP port connectivity checks."""

    @staticmethod
    def check(
        address: str, port: int, timeout: float = 3.0
    ) -> tuple[bool, float | None, str | None]:
        """
        Test whether a TCP port is open on the given address.

        Args:
            address: The target IP address or hostname.
            port: The TCP port number to test.
            timeout: Connection timeout in seconds.

        Returns:
            A tuple of (open, latency_ms, error_message).

        """
        try:
            start = time.monotonic()
            with socket.create_connection((address, port), timeout=timeout):
                latency = round((time.monotonic() - start) * 1000, 2)
            return True, latency, None
        except socket.timeout:
            return False, None, "Connection timed out"
        except socket.gaierror as e:
            return False, None, f"Name resolution failed: {e}"
        except ConnectionRefusedError:
            return False, None, "Connection refused"
        except OSError as e:
            return False, None, str(e)


class SubnetService:
    """Service for IP network calculations."""

    @staticmethod
    def calculate(cidr: str) -> tuple[dict | None, str | None]:
        """
        Calculate subnet details for an IPv4 or IPv6 network.

        Args:
            cidr: IP interface or network in CIDR notation.

        Returns:
            A tuple of (result, error_message).

        """
        try:
            network = ipaddress.ip_network(cidr.strip(), strict=False)
        except ValueError as e:
            return None, f"Invalid CIDR: {e}"

        first_usable = None
        last_usable = None
        if network.version == 4 and network.num_addresses > 2:
            first_usable = str(network.network_address + 1)
            last_usable = str(network.broadcast_address - 1)
        elif network.num_addresses > 0:
            first_usable = str(network.network_address)
            last_usable = str(network.broadcast_address)

        wildcard_mask = None
        if network.version == 4:
            wildcard_mask = str(ipaddress.IPv4Address(int(network.hostmask)))

        return {
            "input": cidr,
            "version": network.version,
            "network": str(network),
            "network_address": str(network.network_address),
            "broadcast_address": str(network.broadcast_address),
            "netmask": str(network.netmask),
            "wildcard_mask": wildcard_mask,
            "prefix_length": network.prefixlen,
            "num_addresses": network.num_addresses,
            "usable_hosts": max(network.num_addresses - 2, 0)
            if network.version == 4 and network.num_addresses > 2
            else network.num_addresses,
            "first_usable": first_usable,
            "last_usable": last_usable,
            "is_private": network.is_private,
            "is_global": network.is_global,
        }, None


class PortScanService:
    """Service for bounded TCP port scans."""

    MAX_PORTS = 100

    @staticmethod
    def _parse_port_part(part: str) -> tuple[set[int] | None, str | None]:
        """Parse one comma-separated port token."""
        if "-" not in part:
            try:
                return {int(part)}, None
            except ValueError:
                return None, f"Invalid port: {part}"

        start_text, end_text = part.split("-", 1)
        try:
            start = int(start_text)
            end = int(end_text)
        except ValueError:
            return None, f"Invalid port range: {part}"
        if start > end:
            return None, f"Invalid port range: {part}"
        if start < 1 or end > 65535:
            return None, "Ports must be between 1 and 65535"
        if end - start + 1 > PortScanService.MAX_PORTS:
            return None, "Port scan is limited to 100 ports"
        return set(range(start, end + 1)), None

    @staticmethod
    def _validate_ports(selected: set[int]) -> tuple[list[int] | None, str | None]:
        """Validate parsed ports and return them sorted."""
        if not selected:
            return None, "No ports supplied"
        if any(port < 1 or port > 65535 for port in selected):
            return None, "Ports must be between 1 and 65535"
        if len(selected) > PortScanService.MAX_PORTS:
            return None, "Port scan is limited to 100 ports"
        return sorted(selected), None

    @staticmethod
    def _parse_ports(ports: str) -> tuple[list[int] | None, str | None]:
        """Parse a comma-separated port/range expression."""
        selected: set[int] = set()
        for chunk in ports.split(","):
            part = chunk.strip()
            if not part:
                continue
            parsed, error = PortScanService._parse_port_part(part)
            if error:
                return None, error
            selected.update(parsed or set())
        return PortScanService._validate_ports(selected)

    @staticmethod
    def scan(
        address: str, ports: str, timeout: float = 1.0
    ) -> tuple[dict | None, str | None]:
        """
        Scan a bounded list of TCP ports.

        Args:
            address: Target host.
            ports: Comma-separated ports or ranges.
            timeout: Per-port timeout.

        Returns:
            A tuple of (result, error_message).

        """
        parsed_ports, error = PortScanService._parse_ports(ports)
        if error:
            return None, error

        start = time.monotonic()
        results = []
        for port in parsed_ports or []:
            is_open, latency, port_error = PortCheckService.check(
                address, port, timeout=timeout
            )
            results.append(
                {
                    "port": port,
                    "open": is_open,
                    "latency": latency,
                    "error": port_error,
                }
            )

        return {
            "address": address,
            "ports": results,
            "elapsed_ms": round((time.monotonic() - start) * 1000, 2),
        }, None


class MailDnsService:
    """Service for mail DNS health checks."""

    @staticmethod
    def _query_records(name: str, record_type: str) -> tuple[list[dict], str | None]:
        records, _ttl, error = _resolve_dns_records(
            dns.resolver.Resolver(), name, record_type
        )
        return records, error

    @staticmethod
    def check(domain: str) -> tuple[dict | None, str | None]:
        """
        Check basic mail DNS records for a domain.

        Args:
            domain: Domain name to inspect.

        Returns:
            A tuple of (result, error_message).

        """
        domain = domain.strip().rstrip(".")
        if not domain:
            return None, "Empty domain"

        mx_records, mx_error = MailDnsService._query_records(domain, "MX")
        txt_records, txt_error = MailDnsService._query_records(domain, "TXT")
        dmarc_records, dmarc_error = MailDnsService._query_records(
            f"_dmarc.{domain}", "TXT"
        )

        spf_records = [
            record
            for record in txt_records
            if record["value"].strip('"').lower().startswith("v=spf1")
        ]
        dmarc_policy_records = [
            record
            for record in dmarc_records
            if record["value"].strip('"').lower().startswith("v=dmarc1")
        ]
        missing = []
        if not mx_records:
            missing.append("MX")
        if not spf_records:
            missing.append("SPF")
        if not dmarc_policy_records:
            missing.append("DMARC")

        return {
            "domain": domain,
            "mx_records": mx_records,
            "spf_records": spf_records,
            "dmarc_records": dmarc_policy_records,
            "missing": missing,
            "errors": {
                "mx": mx_error,
                "txt": txt_error,
                "dmarc": dmarc_error,
            },
        }, None


class WakeOnLanService:
    """Service for Wake On LAN operations."""

    @staticmethod
    def wake(mac_address: str) -> tuple[bool, str | None]:
        """
        Send Wake On LAN magic packet.

        Args:
            mac_address: The MAC address of the target device.

        Returns:
            A tuple of (success, error_message).

        """
        try:
            send_magic_packet(mac_address)
            logger.info(f"Wake On LAN packet sent to {mac_address}")
            return True, None
        except Exception as e:
            logger.error(f"Wake On LAN failed: {e}")
            return False, str(e)
