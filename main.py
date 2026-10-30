# Kim Duy Vương
# 20237410

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import unittest

from teaching_devices import (
    AirConditionerRemote,
    AlertSeverity,
    ConsoleNotificationService,
    DeviceAlertEventArgs,
    DeviceAuditLogger,
    DeviceMonitoringCoordinator,
    DeviceStatus,
    FilteredAlertSubscriber,
    InvalidDeviceReadingException,
    MaintenanceService,
    ProjectorRemote,
    TeachingDevice,
    WirelessMicrophone,
)


def run_demo() -> None:
    projectors = [
        ProjectorRemote("P01", "Điều khiển máy chiếu 1", 100),
        ProjectorRemote("P02", "Điều khiển máy chiếu 2", 60),
        ProjectorRemote("P03", "Điều khiển máy chiếu 3", 25),
    ]
    air_conditioners = [
        AirConditionerRemote("AC01", "Điều khiển điều hòa 1", "D3-301"),
        AirConditionerRemote("AC02", "Điều khiển điều hòa 2", "D3-302"),
    ]
    microphones = [
        WirelessMicrophone("M01", "Micro 1", 100, 90),
        WirelessMicrophone("M02", "Micro 2", 70, 80),
        WirelessMicrophone("M03", "Micro 3", 40, 60),
    ]
    devices: list[TeachingDevice] = [
        *projectors, *air_conditioners, *microphones
    ]
    notification = ConsoleNotificationService()
    audit = DeviceAuditLogger()
    maintenance = MaintenanceService()
    all_alerts: list[DeviceAlertEventArgs] = []
    critical_alerts: list[DeviceAlertEventArgs] = []

    def on_critical(alert: DeviceAlertEventArgs) -> None:
        critical_alerts.append(alert)
        print(f"  [Callback Critical] {alert.device_id}: {alert.message}")

    critical_only = FilteredAlertSubscriber(
        alert_filter=lambda alert: alert.severity is AlertSeverity.CRITICAL,
        action=on_critical,
    )
    alert_recorder = FilteredAlertSubscriber(
        alert_filter=lambda alert: True,
        action=all_alerts.append,
    )
    coordinator = DeviceMonitoringCoordinator(
        devices, notification, audit, maintenance, [critical_only, alert_recorder]
    )

    print("LAB08")
    print(f"Đã tạo {len(devices)} thiết bị: 3 máy chiếu, 2 điều hòa, 3 micro.")
    with coordinator:
        coordinator.subscribe()  # Gọi lại để minh họa không đăng ký trùng.

        print("\n1. Đổi trạng thái P01 sang Borrowed hai lần.")
        projectors[0].change_status(DeviceStatus.BORROWED)
        projectors[0].change_status(DeviceStatus.BORROWED)

        print("\n2. Pin P01: 100 -> 19 -> 10 -> 0.")
        for level in (19, 10, 0):
            projectors[0].update_battery_level(level)

        print("\n3. AC01 mất phản hồi; cập nhật mất phản hồi thêm lần nữa.")
        air_conditioners[0].update_response_state(False)
        air_conditioners[0].update_response_state(False)

        print("\n4. Micro M01: pin xuống 29; tín hiệu xuống 39 rồi 0.")
        microphones[0].update_battery_level(29)
        microphones[0].update_signal_quality(39)
        microphones[0].update_signal_quality(0)

        print("\n5. Thử cập nhật pin P02 bằng 101.")
        try:
            projectors[1].update_battery_level(101)
        except InvalidDeviceReadingException as error:
            print(f"  Đã bắt {type(error).__name__}: {error}")
        print(f"  Pin P02 vẫn là {projectors[1].battery_level}%.")

    print("\n6. Đã dispose coordinator khi ra khỏi khối with.")
    projectors[1].update_battery_level(0)
    print("  P02 đã xuống 0%; các dịch vụ đã hủy đăng ký không nhận thêm.")

    print("\nLỊCH SỬ THAY ĐỔI TRẠNG THÁI")
    for entry in audit.entries:
        print(f"  {entry}")
    print("\nYÊU CẦU BẢO TRÌ")
    for request in maintenance.requests:
        print(f"  {request}")
    print("\nTỔNG KẾT KỊCH BẢN")
    print(f"  Lịch sử trạng thái: {len(audit.entries)} (mong đợi 1)")
    warning_count = sum(alert.severity is AlertSeverity.WARNING for alert in all_alerts)
    critical_count = sum(alert.severity is AlertSeverity.CRITICAL for alert in all_alerts)
    print(
        f"  Cảnh báo trước khi hủy đăng ký: {len(all_alerts)} "
        f"({warning_count} Warning, {critical_count} Critical; mong đợi 6)"
    )
    print(f"  Yêu cầu bảo trì: {len(maintenance.requests)} (mong đợi 3)")
    print(f"  Callback Critical: {len(critical_alerts)} (mong đợi 3)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Lab08 Delegate & Event bằng Python")
    parser.add_argument("--test", action="store_true", help="Chạy 10 kiểm thử tự động")
    args = parser.parse_args()
    if args.test:
        root = Path(__file__).resolve().parent
        suite = unittest.defaultTestLoader.discover(str(root / "tests"))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    run_demo()
    return 0


if __name__ == "__main__":
    # Terminal Windows cũ có thể dùng bảng mã không biểu diễn đủ tiếng Việt.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
