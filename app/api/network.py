"""API routes for network tools."""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, Response, status

from app.models.responses import (
    ErrorResponse,
    MyIpResponse,
    PingResponse,
    TcpPingResponse,
    WakeOnLanResponse,
)
from app.services.network import PingService, TcpPingService, WakeOnLanService
from app.utils.iputils import get_real_ip

router = APIRouter(prefix="/api", tags=["Network Tools"])


@router.get(
    "/ping",
    response_model=PingResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@router.get(
    "/ping/{address}",
    response_model=PingResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def ping(
    request: Request,
    response: Response,
    address: str | None = None,
) -> PingResponse:
    """
    Ping a host and return the average delay.

    Args:
        request: The FastAPI request object.
        response: The FastAPI response object.
        address: Target address. If None, uses the client's IP.

    Returns:
        PingResponse with delay or error message.

    """
    if not address:
        address = get_real_ip(request) or "127.0.0.1"

    delay, error = PingService.ping(address)

    if error:
        if "Name lookup" in error:
            response.status_code = status.HTTP_404_NOT_FOUND
        elif "not reachable" in error:
            response.status_code = status.HTTP_400_BAD_REQUEST
        else:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return PingResponse(error=error)

    return PingResponse(delay=delay)


@router.get(
    "/tcping",
    response_model=TcpPingResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
@router.get(
    "/tcping/{address}",
    response_model=TcpPingResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def tcping(
    request: Request,
    response: Response,
    address: str = "",
    port: Annotated[
        int, Query(ge=1, le=65535, description="Port number to connect to")
    ] = 80,
    timeout: Annotated[
        int, Query(ge=1, le=30, description="Connection timeout in seconds")
    ] = 2,
) -> TcpPingResponse:
    """
    TCP ping a host and return the average connection delay.

    Args:
        request: The FastAPI request object.
        response: The FastAPI response object.
        address: Target address. If empty, uses the client's IP.
        port: Port number to connect to (1-65535).
        timeout: Connection timeout in seconds (1-30).

    Returns:
        TcpPingResponse with delay or error message.

    """
    if not address:
        address = get_real_ip(request) or "127.0.0.1"

    delay, error = TcpPingService.tcping(address, port=port, timeout=timeout)

    if error:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return TcpPingResponse(error=error)

    return TcpPingResponse(delay=delay)


@router.get(
    "/myip",
    response_model=MyIpResponse,
)
async def get_my_ip(request: Request) -> MyIpResponse:
    """
    Get the client's real IP address.

    Args:
        request: The FastAPI request object.

    Returns:
        MyIpResponse with the client's IP address.

    """
    ip = get_real_ip(request) or "unknown"
    return MyIpResponse(ip=ip)


@router.get(
    "/wol/{mac_addr}",
    response_model=WakeOnLanResponse,
    responses={400: {"model": ErrorResponse}},
)
async def wake_on_lan(
    mac_addr: Annotated[
        str,
        Path(
            title="Device MAC address to wakeup",
            pattern=r"^\s*([0-9a-fA-F]{2,2}:){5,5}[0-9a-fA-F]{2,2}\s*$",
            description="MAC address in format XX:XX:XX:XX:XX:XX",
        ),
    ],
) -> WakeOnLanResponse:
    """
    Send Wake On LAN magic packet to wake up a device.

    Args:
        mac_addr: The MAC address of the target device.

    Returns:
        WakeOnLanResponse with result status.

    """
    success, error = WakeOnLanService.wake(mac_addr)

    if not success:
        return WakeOnLanResponse(rst="failed", error=error)

    return WakeOnLanResponse(rst="success")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "webToolSet"}
