# Kim Duy Vương
# 20237410
"""Dữ liệu sự kiện và cơ chế event đồng bộ bằng callback.

Event là giao diện chỉ cho phép đăng ký/hủy đăng ký. _EventSource là
bộ phát nội bộ; chỉ TeachingDevice giữ tham chiếu trực tiếp đến nó.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

from .enums import AlertSeverity, DeviceStatus


@dataclass(frozen=True, slots=True)
class DeviceStatusChangedEventArgs:
    device_id: str
    old_status: DeviceStatus
    new_status: DeviceStatus
    changed_at: datetime


@dataclass(frozen=True, slots=True)
class DeviceAlertEventArgs:
    device_id: str
    message: str
    severity: AlertSeverity
    occurred_at: datetime


TEventArgs = TypeVar("TEventArgs")
EventHandler = Callable[[object, TEventArgs], None]
AlertFilter = Callable[[DeviceAlertEventArgs], bool]
AlertAction = Callable[[DeviceAlertEventArgs], None]


class Event(Generic[TEventArgs]):
    """Public API của event, không có phương thức phát sự kiện.

    subscribe/unsubscribe trả về True nếu thực sự thêm/gỡ handler.
    Một handler đã tồn tại sẽ không được thêm lần thứ hai.
    """

    __slots__ = ("__subscribe", "__unsubscribe")

    def __init__(
        self,
        subscribe: Callable[[EventHandler[TEventArgs]], bool],
        unsubscribe: Callable[[EventHandler[TEventArgs]], bool],
    ) -> None:
        self.__subscribe = subscribe
        self.__unsubscribe = unsubscribe

    def subscribe(self, handler: EventHandler[TEventArgs]) -> bool:
        return self.__subscribe(handler)

    def unsubscribe(self, handler: EventHandler[TEventArgs]) -> bool:
        return self.__unsubscribe(handler)


class _EventSource(Generic[TEventArgs]):
    """Bộ phát nội bộ; dùng bản chụp danh sách handler khi công bố event."""

    def __init__(self) -> None:
        self.__handlers: list[EventHandler[TEventArgs]] = []
        self.__event = Event(self.__subscribe, self.__unsubscribe)

    @property
    def event(self) -> Event[TEventArgs]:
        return self.__event

    def __subscribe(self, handler: EventHandler[TEventArgs]) -> bool:
        if not callable(handler):
            raise TypeError("Handler phải là một hàm hoặc đối tượng callable.")
        if handler in self.__handlers:
            return False
        self.__handlers.append(handler)
        return True

    def __unsubscribe(self, handler: EventHandler[TEventArgs]) -> bool:
        if handler not in self.__handlers:
            return False
        self.__handlers.remove(handler)
        return True

    def publish(self, sender: object, args: TEventArgs) -> None:
        # Thay đổi đăng ký trong handler chỉ ảnh hưởng lần phát kế tiếp.
        # Giữ hành vi đồng bộ: nếu handler ném ngoại lệ, ngoại lệ truyền ra.
        for handler in tuple(self.__handlers):
            handler(sender, args)
