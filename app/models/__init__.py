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
]
