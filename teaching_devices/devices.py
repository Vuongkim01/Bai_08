# Kim Duy Vương
# 20237410
"""Publisher: lớp cơ sở và ba loại thiết bị theo đề bài."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from .enums import AlertSeverity, DeviceStatus
from .events import (
    DeviceAlertEventArgs,
    DeviceStatusChangedEventArgs,
    Event,
    _EventSource,
)
from .exceptions import InvalidDeviceReadingException


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} phải là chuỗi không rỗng.")


def _validate_percentage(device_id: str, value: int) -> None:
    # bool là lớp con của int trong Python, nhưng không phải chỉ số hợp lệ.
    if type(value) is not int:
        raise TypeError("Pin và tín hiệu phải là số nguyên, không nhận bool.")
    if not 0 <= value <= 100:
        raise InvalidDeviceReadingException(device_id, value)


def _alert_transition(
    old_value: int, new_value: int, warning_threshold: int
) -> AlertSeverity | None:
    """Chỉ cảnh báo khi đi vào một mức xấu hơn; phục hồi không cảnh báo."""
    if new_value == 0 and old_value != 0:
        return AlertSeverity.CRITICAL
    if 0 < new_value < warning_threshold and old_value >= warning_threshold:
        return AlertSeverity.WARNING
    return None


class TeachingDevice(ABC):
    # Constructor trừu tượng ngăn khởi tạo trực tiếp lớp cơ sở, đồng thời
    # cung cấp phần khởi tạo chung để constructor lớp con gọi super().
    @abstractmethod
    def __init__(self, device_id: str, name: str) -> None:
        _require_text(device_id, "Mã thiết bị")
        _require_text(name, "Tên thiết bị")
        self.__id = device_id
        self.__name = name
        self.__status = DeviceStatus.AVAILABLE
        self.__status_source = _EventSource[DeviceStatusChangedEventArgs]()
        self.__alert_source = _EventSource[DeviceAlertEventArgs]()

    @property
    def id(self) -> str:
        return self.__id

    @property
    def name(self) -> str:
        return self.__name

    @property
    def status(self) -> DeviceStatus:
        return self.__status

    @property
    def status_changed(self) -> Event[DeviceStatusChangedEventArgs]:
        return self.__status_source.event

    @property
    def alert_raised(self) -> Event[DeviceAlertEventArgs]:
        return self.__alert_source.event

    def change_status(self, new_status: DeviceStatus) -> None:
        if not isinstance(new_status, DeviceStatus):
            raise TypeError("Trạng thái phải thuộc DeviceStatus.")
        if new_status == self.__status:
            return
        old_status = self.__status
        self.__status = new_status
        self._on_status_changed(
            DeviceStatusChangedEventArgs(
                device_id=self.id,
                old_status=old_status,
                new_status=new_status,
                changed_at=datetime.now().astimezone(),
            )
        )

    def _raise_alert(self, message: str, severity: AlertSeverity) -> None:
        self._on_alert_raised(
            DeviceAlertEventArgs(
                device_id=self.id,
                message=message,
                severity=severity,
                occurred_at=datetime.now().astimezone(),
            )
        )

    def _on_status_changed(self, args: DeviceStatusChangedEventArgs) -> None:
        self.__status_source.publish(self, args)

    def _on_alert_raised(self, args: DeviceAlertEventArgs) -> None:
        self.__alert_source.publish(self, args)


class ProjectorRemote(TeachingDevice):
    def __init__(
        self, device_id: str, name: str, battery_level: int = 100
    ) -> None:
        super().__init__(device_id, name)
        _validate_percentage(self.id, battery_level)
        self.__battery_level = battery_level

    @property
    def battery_level(self) -> int:
        return self.__battery_level

    def update_battery_level(self, new_level: int) -> None:
        _validate_percentage(self.id, new_level)
        old_level = self.__battery_level
        self.__battery_level = new_level
        severity = _alert_transition(old_level, new_level, warning_threshold=20)
        if severity is not None:
            self._raise_alert(f"Pin điều khiển máy chiếu còn {new_level}%.", severity)


class AirConditionerRemote(TeachingDevice):
    def __init__(
        self,
        device_id: str,
        name: str,
        assigned_room: str,
        is_responsive: bool = True,
    ) -> None:
        super().__init__(device_id, name)
        _require_text(assigned_room, "Phòng được gán")
        if type(is_responsive) is not bool:
            raise TypeError("Trạng thái phản hồi phải là bool.")
        self.__assigned_room = assigned_room
        self.__is_responsive = is_responsive

    @property
    def assigned_room(self) -> str:
        return self.__assigned_room

    @property
    def is_responsive(self) -> bool:
        return self.__is_responsive

    def update_response_state(self, is_responsive: bool) -> None:
        if type(is_responsive) is not bool:
            raise TypeError("Trạng thái phản hồi phải là bool.")
        was_responsive = self.__is_responsive
        self.__is_responsive = is_responsive
        if was_responsive and not is_responsive:
            self._raise_alert(
                f"Điều khiển điều hòa phòng {self.assigned_room} không phản hồi.",
                AlertSeverity.CRITICAL,
            )


class WirelessMicrophone(TeachingDevice):
    def __init__(
        self,
        device_id: str,
        name: str,
        battery_level: int = 100,
        signal_quality: int = 100,
    ) -> None:
        super().__init__(device_id, name)
        _validate_percentage(self.id, battery_level)
        _validate_percentage(self.id, signal_quality)
        self.__battery_level = battery_level
        self.__signal_quality = signal_quality

    @property
    def battery_level(self) -> int:
        return self.__battery_level

    @property
    def signal_quality(self) -> int:
        return self.__signal_quality

    def update_battery_level(self, new_level: int) -> None:
        _validate_percentage(self.id, new_level)
        old_level = self.__battery_level
        self.__battery_level = new_level
        severity = _alert_transition(old_level, new_level, warning_threshold=30)
        if severity is not None:
            self._raise_alert(f"Pin micro còn {new_level}%.", severity)

    def update_signal_quality(self, new_quality: int) -> None:
        _validate_percentage(self.id, new_quality)
        old_quality = self.__signal_quality
        self.__signal_quality = new_quality
        severity = _alert_transition(old_quality, new_quality, warning_threshold=40)
        if severity is not None:
            self._raise_alert(f"Chất lượng tín hiệu micro còn {new_quality}%.", severity)
