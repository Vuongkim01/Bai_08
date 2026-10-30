# Kim Duy Vương
# 20237410
"""Ngoại lệ nghiệp vụ của thiết bị."""


class InvalidDeviceReadingException(Exception):
    def __init__(self, device_id: str, invalid_value: int) -> None:
        self.__device_id = device_id
        self.__invalid_value = invalid_value
        super().__init__(
            f"Thiết bị {device_id}: giá trị {invalid_value} không thuộc [0, 100]."
        )

    @property
    def device_id(self) -> str:
        return self.__device_id

    @property
    def invalid_value(self) -> int:
        return self.__invalid_value
