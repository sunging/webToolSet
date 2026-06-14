"""Network diagnostic services."""

import logging
import socket
import time

import icmplib
from wakeonlan import send_magic_packet

logger = logging.getLogger(__name__)


class PingService:
    """Service for ICMP ping operations."""

    @staticmethod
    def ping(address: str) -> tuple[float | None, str | None]:
        """
        Perform ICMP ping to the specified address.

        Args:
            address: The target IP address or hostname.

        Returns:
            A tuple of (delay_ms, error_message). delay_ms is None if ping failed.

        """
        try:
            host = icmplib.ping(address, count=4, interval=0.2)
        except icmplib.NameLookupError as e:
            return None, f"Name lookup failed: {e}"
        except Exception as e:
            return None, f"Ping failed: {e}"

        if not host.is_alive:
            return None, "Host is not reachable"

        return host.avg_rtt, None


class TcpPingService:
    """Service for TCP ping operations."""

    @staticmethod
    def tcping(
        address: str, port: int = 80, timeout: int = 2, count: int = 4
    ) -> tuple[float | None, str | None]:
        """
        Perform TCP ping to the specified address and port.

        Args:
            address: The target IP address or hostname.
            port: The target port number.
            timeout: Connection timeout in seconds.
            count: Number of ping attempts.

        Returns:
            A tuple of (delay_ms, error_message). delay_ms is None if tcping failed.

        """
        conn_times = []

        for _ in range(count):
            sock = socket.socket(
                socket.AF_INET6 if ":" in address else socket.AF_INET,
                socket.SOCK_STREAM,
            )
            sock.settimeout(timeout)
            try:
                start = time.time()
                sock.connect((address, port))
                sock.shutdown(socket.SHUT_RD)
                end = time.time()
                conn_times.append(end - start)
            except socket.timeout:
                conn_times.append(0.0)
            except OSError as e:
                conn_times.append(0.0)
                logger.debug(f"TCP connection error: {e}")
            finally:
                sock.close()

        logger.debug(f"TCPing {address}:{port} {count} times: {conn_times}")

        successful_delays = [d for d in conn_times if d > 0]
        if not successful_delays:
            return None, "All TCP ping attempts failed"

        avg_delay = sum(successful_delays) / len(successful_delays)
        return avg_delay, None


class WakeOnLanService:
    """Service for Wake On LAN operations."""

    @staticmethod
    def wake(mac_address: str) -> tuple[bool, str | None]:
        """
        Send Wake On LAN magic packet.

        Args:
            mac_address: The MAC address of the target device.

        Returns:
            A tuple of (success, error_message).

        """
        try:
            send_magic_packet(mac_address)
            logger.info(f"Wake On LAN packet sent to {mac_address}")
            return True, None
        except Exception as e:
            logger.error(f"Wake On LAN failed: {e}")
            return False, str(e)
