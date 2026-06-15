"""API routes for network tools."""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, Response, status

from app.models.responses import (
    DigResponse,
    ErrorResponse,
    MyIpResponse,
    NslookupResponse,
    PingResponse,
    TcpPingResponse,
    TracerouteResponse,
    WakeOnLanResponse,
)
from app.services.network import (
    DnsService,
    PingService,
    TcpPingService,
    TracerouteService,
    WakeOnLanService,
)
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
    "/nslookup/{address}",
    response_model=NslookupResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def nslookup(response: Response, address: str) -> NslookupResponse:
    """
    Resolve a hostname to addresses, or an IP address to a name.

    Args:
        response: The FastAPI response object.
        address: The hostname or IP address to look up.

    Returns:
        NslookupResponse with resolved addresses or error message.

    """
    result, error = DnsService.nslookup(address)

    if error:
        if "does not exist" in error or "No DNS records" in error:
            response.status_code = status.HTTP_404_NOT_FOUND
        else:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return NslookupResponse(name=address, error=error)

    return NslookupResponse(
        name=address,
        server=result["server"],
        addresses=result["addresses"],
        canonical_name=result["canonical_name"],
    )


@router.get(
    "/dig/{address}",
    response_model=DigResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def dig(
    response: Response,
    address: str,
    type: Annotated[
        str,
        Query(
            pattern=r"^(?i:A|AAAA|CNAME|MX|NS|TXT|SOA|PTR|SRV|CAA)$",
            description="DNS record type to query",
        ),
    ] = "A",
) -> DigResponse:
    """
    Perform a dig-style DNS query for a specific record type.

    Args:
        response: The FastAPI response object.
        address: The domain name to query.
        type: DNS record type (A, AAAA, CNAME, MX, NS, TXT, SOA, PTR, SRV, CAA).

    Returns:
        DigResponse with returned records or error message.

    """
    record_type = type.upper()
    result, error = DnsService.dig(address, record_type=record_type)

    if error:
        if "does not exist" in error or "No " in error:
            response.status_code = status.HTTP_404_NOT_FOUND
        else:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DigResponse(name=address, record_type=record_type, error=error)

    return DigResponse(
        name=address,
        record_type=record_type,
        server=result["server"],
        records=result["records"],
        query_time=result["query_time"],
    )


@router.get(
    "/traceroute/{address}",
    response_model=TracerouteResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def traceroute(
    response: Response,
    address: str,
    max_hops: Annotated[
        int, Query(ge=1, le=64, description="Maximum number of hops")
    ] = 30,
    timeout: Annotated[
        int, Query(ge=1, le=30, description="Per-hop timeout in seconds")
    ] = 2,
) -> TracerouteResponse:
    """
    Trace the network path to a host.

    Args:
        response: The FastAPI response object.
        address: The target IP address or hostname.
        max_hops: Maximum number of hops to probe (1-64).
        timeout: Per-hop timeout in seconds (1-30).

    Returns:
        TracerouteResponse with the list of hops or error message.

    """
    hops, error = TracerouteService.traceroute(
        address, max_hops=max_hops, timeout=timeout
    )

    if error:
        if "Name lookup" in error:
            response.status_code = status.HTTP_404_NOT_FOUND
        else:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return TracerouteResponse(address=address, error=error)

    return TracerouteResponse(address=address, hops=hops)


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
