# Kim Duy Vương
# 20237410

from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import partial
from types import TracebackType
from typing import TypeVar

from .devices import TeachingDevice
from .events import Event, EventHandler
from .subscribers import (
    ConsoleNotificationService,
    DeviceAuditLogger,
    FilteredAlertSubscriber,
    MaintenanceService,
)

TEventArgs = TypeVar("TEventArgs")


class DeviceMonitoringCoordinator:
    def __init__(
        self,
        devices: Iterable[TeachingDevice],
        notification_service: ConsoleNotificationService,
        audit_logger: DeviceAuditLogger,
        maintenance_service: MaintenanceService,
        filtered_subscribers: Iterable[FilteredAlertSubscriber] = (),
    ) -> None:
        # Loại trùng theo đối tượng, không gộp hai đối tượng chỉ vì trùng mã.
        unique_devices: list[TeachingDevice] = []
        seen: set[int] = set()
        for device in devices:
            if not isinstance(device, TeachingDevice):
                raise TypeError("Danh sách phải chứa các TeachingDevice.")
            if id(device) not in seen:
                unique_devices.append(device)
                seen.add(id(device))
        self.__devices = tuple(unique_devices)
        self.__notification_service = notification_service
        self.__audit_logger = audit_logger
        self.__maintenance_service = maintenance_service
        self.__filtered_subscribers = tuple(filtered_subscribers)
        self.__undo_subscriptions: list[Callable[[], bool]] = []
        self.__is_subscribed = False
        self.__is_disposed = False

    def _register(
        self, event: Event[TEventArgs], handler: EventHandler[TEventArgs]
    ) -> None:
        # Chỉ lưu thao tác gỡ nếu chính coordinator đã tạo đăng ký này.
        # Một handler do bên ngoài đăng ký trước đó sẽ được giữ nguyên.
        if event.subscribe(handler):
            self.__undo_subscriptions.append(partial(event.unsubscribe, handler))

    def subscribe(self) -> None:
        if self.__is_disposed:
            raise RuntimeError("Không thể đăng ký lại coordinator đã dispose.")
        if self.__is_subscribed:
            return
        try:
            for device in self.__devices:
                self._register(
                    device.alert_raised, self.__notification_service.handle_alert
                )
                self._register(
                    device.status_changed, self.__audit_logger.handle_status_changed
                )
                self._register(
                    device.alert_raised,
                    self.__maintenance_service.handle_critical_alert,
                )
                for subscriber in self.__filtered_subscribers:
                    self._register(device.alert_raised, subscriber.handle_alert)
        except Exception:
            self.unsubscribe()
            raise
        self.__is_subscribed = True

    def unsubscribe(self) -> None:
        for undo in reversed(self.__undo_subscriptions):
            undo()
        self.__undo_subscriptions.clear()
        self.__is_subscribed = False

    def dispose(self) -> None:
        if self.__is_disposed:
            return
        self.unsubscribe()
        self.__is_disposed = True

    def __enter__(self) -> DeviceMonitoringCoordinator:
        self.subscribe()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        self.dispose()
        return False
