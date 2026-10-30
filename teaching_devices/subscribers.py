# Kim Duy Vương
# 20237410
"""Subscriber: chỉ sử dụng sender và dữ liệu công khai của sự kiện."""

from __future__ import annotations

import sys
from typing import TextIO

from .enums import AlertSeverity
from .events import (
    AlertAction,
    AlertFilter,
    DeviceAlertEventArgs,
    DeviceStatusChangedEventArgs,
)


class ConsoleNotificationService:
    def __init__(self, stream: TextIO | None = None) -> None:
        self.__stream = sys.stdout if stream is None else stream

    def handle_alert(self, sender: object, args: DeviceAlertEventArgs) -> None:
        print(
            f"[{args.severity.value}] {args.device_id}: {args.message}",
            file=self.__stream,
        )


class DeviceAuditLogger:
    def __init__(self) -> None:
        self.__entries: list[str] = []

    @property
    def entries(self) -> tuple[str, ...]:
        return tuple(self.__entries)

    def handle_status_changed(
        self, sender: object, args: DeviceStatusChangedEventArgs
    ) -> None:
        self.__entries.append(
            f"{args.changed_at.isoformat(timespec='seconds')}: {args.device_id}, "
            f"{args.old_status.value} -> {args.new_status.value}"
        )


class MaintenanceService:
    def __init__(self) -> None:
        self.__requests: list[str] = []

    @property
    def requests(self) -> tuple[str, ...]:
        return tuple(self.__requests)

    def handle_critical_alert(
        self, sender: object, args: DeviceAlertEventArgs
    ) -> None:
        if args.severity is AlertSeverity.CRITICAL:
            self.__requests.append(
                f"Yêu cầu bảo trì {args.device_id}: {args.message}"
            )


class FilteredAlertSubscriber:
    def __init__(self, alert_filter: AlertFilter, action: AlertAction) -> None:
        if not callable(alert_filter):
            raise TypeError("Bộ lọc phải là callable.")
        if not callable(action):
            raise TypeError("Callback phải là callable.")
        self.__filter = alert_filter
        self.__action = action

    def handle_alert(self, sender: object, args: DeviceAlertEventArgs) -> None:
        if self.__filter(args):
            self.__action(args)
