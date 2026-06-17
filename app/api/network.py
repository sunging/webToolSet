"""API routes for network tools."""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, Response, status

from app.models.responses import (
    DigResponse,
    ErrorResponse,
    MyIpResponse,
    NslookupResponse,
    PingResponse,
    PortCheckResponse,
    ReverseIpResponse,
    TcpPingResponse,
    TracerouteResponse,
    WakeOnLanResponse,
    WhoisResponse,
)
from app.services.network import (
    DnsService,
    PingService,
    PortCheckService,
    ReverseIpService,
    TcpPingService,
    TracerouteService,
    WakeOnLanService,
    WhoisService,
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
    "/reverse-ip",
    response_model=ReverseIpResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@router.get(
    "/reverse-ip/{address}",
    response_model=ReverseIpResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def reverse_ip(
    request: Request,
    response: Response,
    address: str | None = None,
) -> ReverseIpResponse:
    """
    Perform a reverse DNS (PTR) lookup for an IP address.

    Args:
        request: The FastAPI request object.
        response: The FastAPI response object.
        address: The IP address to look up. If None, uses the client's IP.

    Returns:
        ReverseIpResponse with resolved hostnames or error message.

    """
    if not address:
        address = get_real_ip(request) or "127.0.0.1"

    result, error = ReverseIpService.reverse(address)

    if error:
        if "Invalid IP" in error:
            response.status_code = status.HTTP_400_BAD_REQUEST
        elif "No PTR record" in error:
            response.status_code = status.HTTP_404_NOT_FOUND
        else:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ReverseIpResponse(address=address, error=error)

    return ReverseIpResponse(
        address=address,
        server=result["server"],
        hostnames=result["hostnames"],
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
    "/whois/{query}",
    response_model=WhoisResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def whois(
    response: Response,
    query: str,
    timeout: Annotated[
        int, Query(ge=1, le=30, description="Per-connection timeout in seconds")
    ] = 10,
) -> WhoisResponse:
    """
    Look up WHOIS registration information for a domain or IP address.

    Args:
        response: The FastAPI response object.
        query: The domain name or IP address to look up.
        timeout: Per-connection timeout in seconds (1-30).

    Returns:
        WhoisResponse with the raw WHOIS text or error message.

    """
    result, error = WhoisService.whois(query, timeout=timeout)

    if error:
        if "No WHOIS data" in error:
            response.status_code = status.HTTP_404_NOT_FOUND
        else:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return WhoisResponse(query=query, error=error)

    return WhoisResponse(query=query, server=result["server"], raw=result["raw"])


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
    "/port/{address}/{port}",
    response_model=PortCheckResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def port_check(
    response: Response,
    address: str,
    port: Annotated[int, Path(ge=1, le=65535, description="TCP port number to test")],
    timeout: Annotated[
        float, Query(ge=0.1, le=30.0, description="Connection timeout in seconds")
    ] = 3.0,
) -> PortCheckResponse:
    """
    Test whether a TCP port is open on the given host.

    Args:
        response: The FastAPI response object.
        address: The target IP address or hostname.
        port: The TCP port number to test (1-65535).
        timeout: Connection timeout in seconds (0.1-30).

    Returns:
        PortCheckResponse indicating whether the port is open, with optional latency.

    """
    is_open, latency, error = PortCheckService.check(address, port, timeout=timeout)

    if error and "Name resolution" in error:
        response.status_code = status.HTTP_404_NOT_FOUND
    elif error and "timed out" in error:
        response.status_code = status.HTTP_408_REQUEST_TIMEOUT

    return PortCheckResponse(
        address=address,
        port=port,
        open=is_open,
        latency=latency,
        error=error,
    )


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
