"""TCP Ping implementation."""

import socket
import time
import logging

logger = logging.getLogger(__name__)


def tcping(
    ip_address: str, port: int = 80, timeout: int = 1, count: int = 4
) -> list[float]:
    """
    Perform a TCP ping to a specified IP address and port.

    Args:
        ip_address: The IP address to ping.
        port: The port to connect to. Defaults to 80.
        timeout: The timeout for each connection attempt in seconds. Defaults to 1.
        count: The number of ping attempts. Defaults to 4.

    Returns:
        A list of connection times for each ping attempt. A value of 0.0 indicates a timeout.

    """
    conn_times = []

    for n in range(count):
        s = socket.socket(
            socket.AF_INET6 if ":" in ip_address else socket.AF_INET, socket.SOCK_STREAM
        )
        s.settimeout(timeout)
        try:
            start = time.time()

            s.connect((ip_address, port))
            s.shutdown(socket.SHUT_RD)

            end = time.time()
            conn_times.append(end - start)
        except socket.timeout:
            conn_times.append(0.0)
        finally:
            s.close()

    logger.debug(f"TCPing {ip_address}:{port} {count} times: {conn_times}")
    return conn_times
