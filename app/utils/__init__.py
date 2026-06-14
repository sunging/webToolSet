"""Utility functions for network tools."""

from app.utils.iputils import get_real_ip
from app.utils.tcping import tcping

__all__ = ["get_real_ip", "tcping"]
