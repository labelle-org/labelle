from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import NoReturn

LOG = logging.getLogger(__name__)
GITHUB_ISSUE_MAC = "<https://github.com/labelle-org/labelle/issues/5>"
GITHUB_ISSUE_UDEV = "<https://github.com/labelle-org/labelle/issues/6>"


class DeviceError(RuntimeError):
    pass


class Device(ABC):
    @property
    @abstractmethod
    def hash(self) -> str:
        pass

    @property
    @abstractmethod
    def manufacturer(self) -> str | None:
        pass

    @property
    @abstractmethod
    def product(self) -> str | None:
        pass

    @property
    @abstractmethod
    def serial_number(self) -> str | None:
        pass

    @property
    @abstractmethod
    def connection_id(self) -> str:
        pass

    @staticmethod
    @abstractmethod
    def _is_supported_vendor(dev) -> bool:
        return False

    @property
    @abstractmethod
    def is_supported(self) -> bool:
        pass

    @classmethod
    def supported_devices(cls) -> set[Device]:
        results = set()
        for subclass in Device.__subclasses__():
            results |= subclass.supported_devices()
        return results

    @property
    @abstractmethod
    def device_info(self) -> str:
        pass

    @abstractmethod
    def _instruct_on_access_denied(self) -> NoReturn:
        exit(-1)

    @abstractmethod
    def _instruct_on_access_denied_linux(self) -> NoReturn:
        exit(-2)

    @abstractmethod
    def setup(self) -> None:
        pass

    @abstractmethod
    def dispose(self) -> None:
        pass

    def is_match(self, patterns: list[str] | None) -> bool:
        if patterns is None:
            return True
        match = True
        for pattern in patterns:
            pattern = pattern.lower()
            match &= (
                pattern in (self.manufacturer or "").lower()
                or pattern in (self.product or "").lower()
                or pattern in (self.serial_number or "").lower()
            )
        return match

    @abstractmethod
    def execute_command(
        self, cmd: list[int], synwait: int | None, response: bool
    ) -> list[int] | None:
        pass
