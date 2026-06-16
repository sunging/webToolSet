"""Response models for API endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class PingResponse(BaseModel):
    """Response model for ping endpoint."""

    delay: float | None = Field(
        None, description="Average round-trip time in milliseconds"
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


class PortCheckResponse(BaseModel):
    """Response model for port check endpoint."""

    address: str = Field(description="Target address")
    port: int = Field(description="Target port number")
    open: bool = Field(description="Whether the port is open")
    latency: float | None = Field(None, description="Connection latency in milliseconds")
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
