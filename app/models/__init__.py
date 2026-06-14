"""Data models package."""

from app.models.responses import (
    ErrorResponse,
    MyIpResponse,
    PingResponse,
    TcpPingResponse,
    WakeOnLanResponse,
)

__all__ = [
    "ErrorResponse",
    "MyIpResponse",
    "PingResponse",
    "TcpPingResponse",
    "WakeOnLanResponse",
]
