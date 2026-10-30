# Kim Duy Vương
# 20237410

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from io import StringIO
import unittest

from teaching_devices import (
    AirConditionerRemote,
    AlertSeverity,
    ConsoleNotificationService,
    DeviceAlertEventArgs,
    DeviceAuditLogger,
    DeviceMonitoringCoordinator,
    DeviceStatus,
    DeviceStatusChangedEventArgs,
    FilteredAlertSubscriber,
    InvalidDeviceReadingException,
    MaintenanceService,
    ProjectorRemote,
    WirelessMicrophone,
)


class Lab08Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.projectors = [
            ProjectorRemote("P01", "Máy chiếu 1", 100),
            ProjectorRemote("P02", "Máy chiếu 2", 60),
            ProjectorRemote("P03", "Máy chiếu 3", 25),
        ]
        self.air_conditioners = [
            AirConditionerRemote("AC01", "Điều hòa 1", "D3-301"),
            AirConditionerRemote("AC02", "Điều hòa 2", "D3-302"),
        ]
        self.microphones = [
            WirelessMicrophone("M01", "Micro 1", 100, 90),
            WirelessMicrophone("M02", "Micro 2", 70, 80),
            WirelessMicrophone("M03", "Micro 3", 40, 60),
        ]
        self.devices = [
            *self.projectors, *self.air_conditioners, *self.microphones
        ]
        self.output = StringIO()
        self.notification = ConsoleNotificationService(self.output)
        self.audit = DeviceAuditLogger()
        self.maintenance = MaintenanceService()
        self.critical_alerts: list[DeviceAlertEventArgs] = []
        self.critical_only = FilteredAlertSubscriber(
            lambda alert: alert.severity is AlertSeverity.CRITICAL,
            self.critical_alerts.append,
        )
        self.coordinator = DeviceMonitoringCoordinator(
            self.devices,
            self.notification,
            self.audit,
            self.maintenance,
            [self.critical_only],
        )
        self.coordinator.subscribe()
        self.addCleanup(self.coordinator.dispose)

    def test_01_status_event_and_audit(self) -> None:
        """Đúng dữ liệu, cập nhật trước event, dữ liệu event chỉ đọc."""
        device = self.projectors[0]
        received = []

        def capture(sender: object, args: DeviceStatusChangedEventArgs) -> None:
            received.append((sender, args, device.status))

        device.status_changed.subscribe(capture)
        before = datetime.now().astimezone()
        device.change_status(DeviceStatus.BORROWED)
        after = datetime.now().astimezone()

        self.assertEqual(len(received), 1)
        sender, args, observed_status = received[0]
        self.assertIs(sender, device)
        self.assertEqual(args.device_id, device.id)
        self.assertIs(args.old_status, DeviceStatus.AVAILABLE)
        self.assertIs(args.new_status, DeviceStatus.BORROWED)
        self.assertIs(observed_status, DeviceStatus.BORROWED)
        self.assertLessEqual(before, args.changed_at)
        self.assertLessEqual(args.changed_at, after)
        self.assertEqual(len(self.audit.entries), 1)
        self.assertIn("P01, Available -> Borrowed", self.audit.entries[0])
        with self.assertRaises(FrozenInstanceError):
            args.device_id = "REPLACED"
        with self.assertRaises(AttributeError):
            device.status = DeviceStatus.AVAILABLE
        self.assertFalse(hasattr(device.status_changed, "publish"))
        self.assertFalse(hasattr(device.alert_raised, "publish"))

    def test_02_unchanged_status_has_no_event(self) -> None:
        """Cập nhật cùng trạng thái không phát event hoặc ghi log."""
        received = []
        for device in self.devices:
            with self.subTest(device=device.id):
                device.status_changed.subscribe(lambda sender, args: received.append(args))
                device.change_status(DeviceStatus.AVAILABLE)
                self.assertIs(device.status, DeviceStatus.AVAILABLE)
        self.assertEqual(received, [])
        self.assertEqual(self.audit.entries, ())

    def test_03_projector_battery_thresholds_and_recovery(self) -> None:
        """Biên 20, Warning, Critical, chống lặp và phục hồi."""
        device = self.projectors[0]
        received = []
        device.alert_raised.subscribe(lambda sender, args: received.append(args))
        steps = [
            (100, 0), (20, 0), (19, 1), (10, 1), (1, 1),
            (0, 2), (0, 2), (10, 2), (100, 2), (19, 3),
        ]
        for new_level, expected_count in steps:
            with self.subTest(new_level=new_level, count=expected_count):
                device.update_battery_level(new_level)
                self.assertEqual(device.battery_level, new_level)
                self.assertEqual(len(received), expected_count)
        self.assertEqual(
            [args.severity for args in received],
            [AlertSeverity.WARNING, AlertSeverity.CRITICAL, AlertSeverity.WARNING],
        )
        # Nhảy trực tiếp từ vùng bình thường xuống 0 chỉ có một Critical.
        other_received = []
        other = self.projectors[1]
        other.alert_raised.subscribe(lambda sender, args: other_received.append(args))
        other.update_battery_level(0)
        self.assertEqual(len(other_received), 1)
        self.assertIs(other_received[0].severity, AlertSeverity.CRITICAL)

    def test_04_microphone_battery_and_signal_are_independent(self) -> None:
        """Pin biên 30 và tín hiệu biên 40 được kiểm tra độc lập."""
        for device in self.microphones:
            with self.subTest(device=device.id):
                received = []

                def capture(sender: object, args: DeviceAlertEventArgs) -> None:
                    self.assertIs(sender, device)
                    self.assertEqual(args.device_id, device.id)
                    received.append(args)

                device.alert_raised.subscribe(capture)
                device.update_battery_level(30)
                self.assertEqual(len(received), 0)
                device.update_battery_level(29)
                device.update_battery_level(10)
                self.assertEqual(len(received), 1)
                device.update_battery_level(0)
                device.update_battery_level(0)
                self.assertEqual(len(received), 2)
                device.update_signal_quality(40)
                self.assertEqual(len(received), 2)
                device.update_signal_quality(39)
                device.update_signal_quality(20)
                self.assertEqual(len(received), 3)
                device.update_signal_quality(0)
                device.update_signal_quality(0)
                self.assertEqual(len(received), 4)
                self.assertEqual(
                    [args.severity for args in received],
                    [AlertSeverity.WARNING, AlertSeverity.CRITICAL] * 2,
                )
                self.assertIn("Pin micro", received[1].message)
                self.assertIn("tín hiệu", received[3].message)

    def test_05_air_conditioner_no_repeated_failure_alert(self) -> None:
        """Mất phản hồi cảnh báo một lần; phục hồi cho phép phát hiện lỗi mới."""
        for device in self.air_conditioners:
            with self.subTest(device=device.id):
                received = []
                device.alert_raised.subscribe(lambda sender, args: received.append(args))
                for responsive, expected in [
                    (True, 0), (False, 1), (False, 1), (True, 1), (False, 2)
                ]:
                    device.update_response_state(responsive)
                    self.assertIs(device.is_responsive, responsive)
                    self.assertEqual(len(received), expected)
                self.assertTrue(
                    all(args.severity is AlertSeverity.CRITICAL for args in received)
                )
                self.assertIn(device.assigned_room, received[0].message)

    def test_06_invalid_readings_preserve_state_without_events(self) -> None:
        """Giá trị ngoài [0,100] bị từ chối trước mọi thay đổi hoặc event."""
        received = []
        readings = []
        for device in [*self.projectors, *self.microphones]:
            device.alert_raised.subscribe(lambda sender, args: received.append(args))
            readings.append((device, "battery_level", device.update_battery_level))
        for device in self.microphones:
            readings.append((device, "signal_quality", device.update_signal_quality))
        for device, attribute, update in readings:
            original = getattr(device, attribute)
            for value in (-1, 101):
                with self.subTest(device=device.id, reading=attribute, value=value):
                    with self.assertRaises(InvalidDeviceReadingException) as caught:
                        update(value)
                    self.assertEqual(caught.exception.device_id, device.id)
                    self.assertEqual(caught.exception.invalid_value, value)
                    self.assertEqual(getattr(device, attribute), original)
            for value in (True, 12.5):
                with self.subTest(device=device.id, invalid_type=type(value).__name__):
                    with self.assertRaises(TypeError):
                        update(value)
                    self.assertEqual(getattr(device, attribute), original)
        self.assertEqual(received, [])
        self.assertEqual(self.output.getvalue(), "")
        self.assertEqual(self.maintenance.requests, ())

    def test_07_multiple_subscribers_and_critical_maintenance(self) -> None:
        """Nhiều subscriber xử lý cùng event; bảo trì chỉ nhận Critical."""
        device = self.projectors[0]
        received = []
        device.alert_raised.subscribe(lambda sender, args: received.append(args))
        device.update_battery_level(19)
        self.assertEqual(len(self.output.getvalue().splitlines()), 1)
        self.assertEqual(self.maintenance.requests, ())
        self.assertEqual(self.critical_alerts, [])
        device.update_battery_level(0)
        self.assertEqual(len(received), 2)
        self.assertEqual(len(self.output.getvalue().splitlines()), 2)
        self.assertEqual(len(self.maintenance.requests), 1)
        self.assertEqual(len(self.critical_alerts), 1)
        self.assertIs(self.critical_alerts[0], received[1])
        self.assertIs(device.status, DeviceStatus.AVAILABLE)
        self.assertEqual(self.audit.entries, ())
        # Subscriber mới được thêm mà không chỉnh sửa lớp thiết bị.
        late_received = []
        device.alert_raised.subscribe(lambda sender, args: late_received.append(args))
        device.update_battery_level(100)
        device.update_battery_level(0)
        self.assertEqual(len(late_received), 1)

    def test_08_filtered_callback_only_runs_on_matching_alerts(self) -> None:
        """Thay chính sách lọc bằng callable truyền vào constructor."""
        executed = []
        subscriber = FilteredAlertSubscriber(
            lambda alert: (
                alert.severity is AlertSeverity.CRITICAL and alert.device_id == "M01"
            ),
            executed.append,
        )
        samples = [
            ("M01", AlertSeverity.INFORMATION),
            ("M01", AlertSeverity.WARNING),
            ("P01", AlertSeverity.CRITICAL),
            ("M01", AlertSeverity.CRITICAL),
        ]
        for device_id, severity in samples:
            subscriber.handle_alert(
                self,
                DeviceAlertEventArgs(
                    device_id, "Cảnh báo kiểm thử", severity,
                    datetime.now().astimezone(),
                ),
            )
        self.assertEqual(len(executed), 1)
        self.assertEqual(executed[0].device_id, "M01")
        self.assertIs(executed[0].severity, AlertSeverity.CRITICAL)

    def test_09_subscribe_is_idempotent_with_repeated_device(self) -> None:
        """Subscribe nhiều lần và thiết bị trùng không nhân đôi handler."""
        self.coordinator.unsubscribe()
        device = self.projectors[0]
        coordinator = DeviceMonitoringCoordinator(
            [device, device], self.notification, self.audit, self.maintenance,
            [self.critical_only, self.critical_only],
        )
        self.addCleanup(coordinator.dispose)
        coordinator.subscribe()
        coordinator.subscribe()
        coordinator.subscribe()
        device.change_status(DeviceStatus.BORROWED)
        device.update_battery_level(0)
        self.assertEqual(len(self.audit.entries), 1)
        self.assertEqual(len(self.output.getvalue().splitlines()), 1)
        self.assertEqual(len(self.maintenance.requests), 1)
        self.assertEqual(len(self.critical_alerts), 1)

    def test_10_unsubscribe_dispose_and_external_subscription(self) -> None:
        """Hủy đúng đăng ký; dispose an toàn; thiết bị vẫn hoạt động."""
        self.coordinator.unsubscribe()
        self.coordinator.unsubscribe()
        device = self.projectors[0]
        external_alerts = []
        external_handler = lambda sender, args: external_alerts.append(args)
        device.alert_raised.subscribe(external_handler)
        # Cùng một handler của notification đã được bên ngoài đăng ký trước.
        device.alert_raised.subscribe(self.notification.handle_alert)
        self.coordinator.subscribe()
        self.coordinator.unsubscribe()
        device.change_status(DeviceStatus.BORROWED)
        device.update_battery_level(0)
        self.assertEqual(device.battery_level, 0)
        self.assertEqual(self.audit.entries, ())
        self.assertEqual(self.maintenance.requests, ())
        self.assertEqual(len(external_alerts), 1)
        self.assertEqual(len(self.output.getvalue().splitlines()), 1)
        # Notification bên ngoài vẫn còn; gỡ nó để tiếp tục kiểm tra vòng đời.
        device.alert_raised.unsubscribe(self.notification.handle_alert)
        self.coordinator.subscribe()
        device.update_battery_level(100)
        device.update_battery_level(0)
        self.assertEqual(len(self.maintenance.requests), 1)
        self.coordinator.dispose()
        self.coordinator.dispose()
        device.update_battery_level(100)
        device.update_battery_level(0)
        self.assertEqual(len(external_alerts), 3)
        self.assertEqual(len(self.maintenance.requests), 1)
        self.assertEqual(len(self.output.getvalue().splitlines()), 2)
        with self.assertRaises(RuntimeError):
            self.coordinator.subscribe()
        # Context manager phải hủy đăng ký cả khi khối with gặp ngoại lệ.
        other = self.projectors[1]
        scoped = DeviceMonitoringCoordinator(
            [other], self.notification, self.audit, self.maintenance
        )
        with self.assertRaisesRegex(ValueError, "lỗi trong with"):
            with scoped:
                other.update_battery_level(0)
                raise ValueError("lỗi trong with")
        request_count = len(self.maintenance.requests)
        other.update_battery_level(100)
        other.update_battery_level(0)
        self.assertEqual(len(self.maintenance.requests), request_count)


if __name__ == "__main__":
    unittest.main(verbosity=2)
