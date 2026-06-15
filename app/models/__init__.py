"""Data models package."""

from app.models.responses import (
    DigResponse,
    DnsRecord,
    ErrorResponse,
    MyIpResponse,
    NslookupResponse,
    PingResponse,
    TcpPingResponse,
    TracerouteHop,
    TracerouteResponse,
    WakeOnLanResponse,
    WhoisResponse,
)

__all__ = [
    "DigResponse",
    "DnsRecord",
    "ErrorResponse",
    "MyIpResponse",
    "NslookupResponse",
    "PingResponse",
    "TcpPingResponse",
    "TracerouteHop",
    "TracerouteResponse",
    "WakeOnLanResponse",
    "WhoisResponse",
]
