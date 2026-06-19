"""Response models for API endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class PingResponse(BaseModel):
    """Response model for ping endpoint."""

    address: str | None = Field(None, description="Queried address")
    resolved_address: str | None = Field(None, description="Resolved IP address")
    delay: float | None = Field(
        None, description="Average round-trip time in milliseconds"
    )
    sent: int | None = Field(None, description="Packets sent")
    received: int | None = Field(None, description="Packets received")
    packet_loss: float | None = Field(None, description="Packet loss percentage")
    min_rtt: float | None = Field(None, description="Minimum RTT in milliseconds")
    avg_rtt: float | None = Field(None, description="Average RTT in milliseconds")
    max_rtt: float | None = Field(None, description="Maximum RTT in milliseconds")
    jitter: float | None = Field(None, description="Jitter in milliseconds")
    stddev: float | None = Field(None, description="RTT standard deviation")
    probes: list[dict[str, Any]] = Field(
        default_factory=list, description="Per-probe ping results"
    )
    error: str | None = Field(None, description="Error message if ping failed")


class TcpPingResponse(BaseModel):
    """Response model for tcping endpoint."""

    delay: float | None = Field(
        None, description="Average connection time in milliseconds"
    )
    error: str | None = Field(None, description="Error message if tcping failed")


class NslookupResponse(BaseModel):
    """Response model for nslookup endpoint."""

    name: str = Field(description="Queried name")
    server: str | None = Field(None, description="DNS server used for the query")
    addresses: list[str] = Field(
        default_factory=list, description="Resolved addresses or PTR names"
    )
    canonical_name: str | None = Field(
        None, description="Canonical name (CNAME) if present"
    )
    error: str | None = Field(None, description="Error message if lookup failed")


class ReverseIpResponse(BaseModel):
    """Response model for reverse IP (PTR) lookup endpoint."""

    address: str = Field(description="Queried IP address")
    server: str | None = Field(None, description="DNS server used for the query")
    hostnames: list[str] = Field(
        default_factory=list, description="Resolved PTR hostnames"
    )
    error: str | None = Field(None, description="Error message if lookup failed")


class DnsRecord(BaseModel):
    """A single DNS record."""

    type: str = Field(description="Record type")
    value: str = Field(description="Record value")
    ttl: int | None = Field(None, description="Time to live in seconds")


class DigResponse(BaseModel):
    """Response model for dig endpoint."""

    name: str = Field(description="Queried name")
    record_type: str = Field(description="Queried record type")
    server: str | None = Field(None, description="DNS server used for the query")
    records: list[DnsRecord] = Field(
        default_factory=list, description="Returned DNS records"
    )
    query_time: float | None = Field(None, description="Query time in milliseconds")
    error: str | None = Field(None, description="Error message if query failed")


class DnsCompareResult(BaseModel):
    """DNS comparison result for one resolver."""

    resolver: str = Field(description="Resolver label")
    servers: list[str] = Field(default_factory=list, description="Resolver servers")
    records: list[DnsRecord] = Field(default_factory=list, description="DNS records")
    ttl: int | None = Field(None, description="Record TTL")
    query_time: float = Field(description="Query time in milliseconds")
    error: str | None = Field(None, description="Resolver-specific error")


class DnsCompareResponse(BaseModel):
    """Response model for DNS resolver comparison."""

    name: str = Field(description="Queried name")
    record_type: str = Field(description="Queried record type")
    results: list[DnsCompareResult] = Field(
        default_factory=list, description="Per-resolver results"
    )
    error: str | None = Field(None, description="Error message if comparison failed")


class TracerouteHop(BaseModel):
    """A single traceroute hop."""

    distance: int = Field(description="Hop number (distance from source)")
    address: str | None = Field(None, description="IP address of the hop")
    avg_rtt: float | None = Field(
        None, description="Average round-trip time in milliseconds"
    )
    is_alive: bool = Field(False, description="Whether the hop responded")


class TracerouteResponse(BaseModel):
    """Response model for traceroute endpoint."""

    address: str = Field(description="Target address")
    hops: list[TracerouteHop] = Field(
        default_factory=list, description="List of traceroute hops"
    )
    error: str | None = Field(None, description="Error message if traceroute failed")


class WhoisResponse(BaseModel):
    """Response model for whois endpoint."""

    query: str = Field(description="Queried domain or IP address")
    server: str | None = Field(None, description="WHOIS server that answered")
    raw: str | None = Field(None, description="Raw WHOIS response text")
    error: str | None = Field(None, description="Error message if lookup failed")


class RedirectHop(BaseModel):
    """A single HTTP redirect hop."""

    status_code: int = Field(description="Redirect response status")
    url: str = Field(description="Redirect source URL")
    location: str | None = Field(None, description="Location header")


class HttpCheckResponse(BaseModel):
    """Response model for HTTP/HTTPS checks."""

    url: str = Field(description="Requested URL")
    final_url: str | None = Field(None, description="Final URL after redirects")
    status_code: int | None = Field(None, description="HTTP status code")
    reason_phrase: str | None = Field(None, description="HTTP reason phrase")
    elapsed_ms: float | None = Field(None, description="Request time in milliseconds")
    redirects: list[RedirectHop] = Field(
        default_factory=list, description="Redirect history"
    )
    response_size: int | None = Field(None, description="Response size in bytes")
    content_type: str | None = Field(None, description="Response content type")
    server: str | None = Field(None, description="Server header")
    headers: dict[str, str] = Field(default_factory=dict, description="Response headers")
    security_headers: dict[str, str] = Field(
        default_factory=dict, description="Detected security headers"
    )
    cache_headers: dict[str, str] = Field(
        default_factory=dict, description="Detected cache headers"
    )
    error: str | None = Field(None, description="Error message if request failed")


class RequestInspectorResponse(BaseModel):
    """Response model for HTTP request inspection."""

    request: dict[str, Any] = Field(default_factory=dict, description="Request summary")
    response: dict[str, Any] = Field(
        default_factory=dict, description="Response summary"
    )
    redirects: list[RedirectHop] = Field(
        default_factory=list, description="Redirect history"
    )
    error: str | None = Field(None, description="Error message if inspection failed")


class TlsCheckResponse(BaseModel):
    """Response model for TLS certificate checks."""

    host: str = Field(description="Target host")
    port: int = Field(description="Target port")
    subject: dict[str, str] = Field(default_factory=dict, description="Certificate subject")
    issuer: dict[str, str] = Field(default_factory=dict, description="Certificate issuer")
    subject_alt_names: list[str] = Field(
        default_factory=list, description="Subject alternative names"
    )
    not_before: str | None = Field(None, description="Certificate valid from")
    not_after: str | None = Field(None, description="Certificate valid until")
    days_remaining: int | None = Field(None, description="Days until expiration")
    expired: bool | None = Field(None, description="Whether the certificate expired")
    protocol: str | None = Field(None, description="Negotiated TLS protocol")
    cipher: str | None = Field(None, description="Negotiated cipher")
    error: str | None = Field(None, description="Error message if check failed")


class PortCheckResponse(BaseModel):
    """Response model for port check endpoint."""

    address: str = Field(description="Target address")
    port: int = Field(description="Target port number")
    open: bool = Field(description="Whether the port is open")
    latency: float | None = Field(None, description="Connection latency in milliseconds")
    error: str | None = Field(None, description="Error message if check failed")


class MtrHop(BaseModel):
    """Aggregated MTR hop statistics."""

    distance: int = Field(description="Hop number")
    address: str | None = Field(None, description="Representative hop address")
    sent: int = Field(description="Probes sent")
    received: int = Field(description="Responses received")
    packet_loss: float = Field(description="Packet loss percentage")
    best_rtt: float | None = Field(None, description="Best RTT in milliseconds")
    avg_rtt: float | None = Field(None, description="Average RTT in milliseconds")
    worst_rtt: float | None = Field(None, description="Worst RTT in milliseconds")
    jitter: float | None = Field(None, description="RTT jitter in milliseconds")
    addresses: dict[str, int] = Field(
        default_factory=dict, description="Observed addresses and counts"
    )


class MtrResponse(BaseModel):
    """Response model for MTR-style route quality analysis."""

    address: str = Field(description="Target address")
    cycles: int | None = Field(None, description="Trace cycles")
    max_hops: int | None = Field(None, description="Maximum hop count")
    hops: list[MtrHop] = Field(default_factory=list, description="Aggregated hops")
    summary: str | None = Field(None, description="Route quality summary")
    error: str | None = Field(None, description="Error message if MTR failed")


class SubnetResponse(BaseModel):
    """Response model for subnet calculations."""

    input: str = Field(description="Input CIDR")
    version: int | None = Field(None, description="IP version")
    network: str | None = Field(None, description="Network in CIDR notation")
    network_address: str | None = Field(None, description="Network address")
    broadcast_address: str | None = Field(None, description="Broadcast address")
    netmask: str | None = Field(None, description="Subnet mask")
    wildcard_mask: str | None = Field(None, description="Wildcard mask")
    prefix_length: int | None = Field(None, description="Prefix length")
    num_addresses: int | None = Field(None, description="Total address count")
    usable_hosts: int | None = Field(None, description="Usable host count")
    first_usable: str | None = Field(None, description="First usable address")
    last_usable: str | None = Field(None, description="Last usable address")
    is_private: bool | None = Field(None, description="Whether network is private")
    is_global: bool | None = Field(None, description="Whether network is global")
    error: str | None = Field(None, description="Error message if calculation failed")


class PortScanItem(BaseModel):
    """Single port scan result."""

    port: int = Field(description="TCP port")
    open: bool = Field(description="Whether the port is open")
    latency: float | None = Field(None, description="Connection latency")
    error: str | None = Field(None, description="Port-specific error")


class PortScanResponse(BaseModel):
    """Response model for bounded TCP port scans."""

    address: str = Field(description="Target address")
    ports: list[PortScanItem] = Field(default_factory=list, description="Port results")
    elapsed_ms: float | None = Field(None, description="Total scan time")
    error: str | None = Field(None, description="Error message if scan failed")


class MailDnsResponse(BaseModel):
    """Response model for mail DNS health checks."""

    domain: str = Field(description="Checked domain")
    mx_records: list[DnsRecord] = Field(default_factory=list, description="MX records")
    spf_records: list[DnsRecord] = Field(default_factory=list, description="SPF records")
    dmarc_records: list[DnsRecord] = Field(
        default_factory=list, description="DMARC records"
    )
    missing: list[str] = Field(default_factory=list, description="Missing mail records")
    errors: dict[str, str | None] = Field(
        default_factory=dict, description="Lookup errors by record category"
    )
    error: str | None = Field(None, description="Error message if check failed")


class WakeOnLanResponse(BaseModel):
    """Response model for wake on lan endpoint."""

    rst: str = Field(description="Result status")
    error: str | None = Field(None, description="Error message if wake on lan failed")


class MyIpResponse(BaseModel):
    """Response model for myip endpoint."""

    ip: str = Field(description="Client IP address")


class ErrorResponse(BaseModel):
    """Generic error response model."""

    error: str = Field(description="Error message")
    detail: Any = Field(None, description="Additional error details")
