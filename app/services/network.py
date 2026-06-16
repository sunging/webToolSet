"""Network diagnostic services."""

import ipaddress
import logging
import re
import socket
import time

import dns.exception
import dns.rdatatype
import dns.resolver
import dns.reversename
import icmplib
from wakeonlan import send_magic_packet

logger = logging.getLogger(__name__)


class PingService:
    """Service for ICMP ping operations."""

    @staticmethod
    def ping(address: str) -> tuple[float | None, str | None]:
        """
        Perform ICMP ping to the specified address.

        Args:
            address: The target IP address or hostname.

        Returns:
            A tuple of (delay_ms, error_message). delay_ms is None if ping failed.

        """
        try:
            host = icmplib.ping(address, count=4, interval=0.2)
        except icmplib.NameLookupError as e:
            return None, f"Name lookup failed: {e}"
        except Exception as e:
            return None, f"Ping failed: {e}"

        if not host.is_alive:
            return None, "Host is not reachable"

        return host.avg_rtt, None


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

        try:
            ipaddress.ip_address(name)
            is_ip = True
        except ValueError:
            is_ip = False

        addresses: list[str] = []
        canonical_name: str | None = None

        try:
            if is_ip:
                rev_name = dns.reversename.from_address(name)
                answers = resolver.resolve(rev_name, "PTR")
                addresses = [str(r).rstrip(".") for r in answers]
            else:
                for rtype in ("A", "AAAA"):
                    try:
                        answers = resolver.resolve(name, rtype)
                    except dns.resolver.NoAnswer:
                        continue
                    cname = str(answers.canonical_name).rstrip(".")
                    if cname and cname != name.rstrip("."):
                        canonical_name = cname
                    addresses.extend(str(r) for r in answers)
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

        try:
            start = time.time()
            answers = resolver.resolve(name, record_type)
            query_time = (time.time() - start) * 1000
        except dns.resolver.NXDOMAIN:
            return None, f"Name does not exist: {name}"
        except dns.resolver.NoAnswer:
            return None, f"No {record_type} records found for {name}"
        except dns.resolver.NoNameservers:
            return None, "No nameservers could answer the query"
        except dns.exception.Timeout:
            return None, "DNS query timed out"
        except dns.rdatatype.UnknownRdatatype:
            return None, f"Unknown record type: {record_type}"
        except Exception as e:
            logger.debug(f"dig error: {e}")
            return None, f"DNS query failed: {e}"

        ttl = answers.rrset.ttl if answers.rrset is not None else None
        records = [
            {"type": record_type, "value": str(rdata), "ttl": ttl}
            for rdata in answers
        ]

        return {
            "server": server,
            "records": records,
            "query_time": query_time,
        }, None


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
