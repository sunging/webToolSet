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
