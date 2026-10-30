# Kim Duy Vương
# 20237410
"""Các enum dùng chung trong bài thực hành tuần 8."""

from enum import Enum


class DeviceStatus(Enum):
    AVAILABLE = "Available"
    BORROWED = "Borrowed"
    UNDER_MAINTENANCE = "UnderMaintenance"


class AlertSeverity(Enum):
    INFORMATION = "Information"
    WARNING = "Warning"
    CRITICAL = "Critical"
