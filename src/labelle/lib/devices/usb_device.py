from __future__ import annotations

import logging
from contextlib import contextmanager

import hid

from labelle.lib.constants import (
    DEV_VENDOR,
    SUPPORTED_PRODUCTS,
)

LOG = logging.getLogger(__name__)
GITHUB_ISSUE_MAC = "<https://github.com/labelle-org/labelle/issues/5>"
GITHUB_ISSUE_UDEV = "<https://github.com/labelle-org/labelle/issues/6>"


class UsbDeviceError(RuntimeError):
    pass


class UsbDevice:
    _dev: dict

    def __init__(self, dev: dict) -> None:
        self._dev = dev

    @property
    def hash(self):
        return f"<{self.manufacturer}|{self.product}|{self.serial_number}>"

    def _get_dev_attribute(self, attr):
        return self._dev.get(attr)

    @property
    def manufacturer(self):
        return self._get_dev_attribute("manufacturer_string")

    @property
    def product(self):
        return self._get_dev_attribute("product_string")

    @property
    def serial_number(self):
        return self._get_dev_attribute("serial_number")

    @property
    def product_id(self):
        return self._get_dev_attribute("product_id")

    @property
    def vendor_id(self):
        return self._get_dev_attribute("vendor_id")

    @staticmethod
    def _is_supported_vendor(dev: dict):
        return dev["vendor_id"] == DEV_VENDOR

    @property
    def is_supported(self):
        return (
            self._is_supported_vendor(self._dev)
            and self.product_id in SUPPORTED_PRODUCTS
        )

    @contextmanager
    def hid_device(self) -> hid.device:
        hid_device = hid.device()
        try:
            hid_device.open(self.vendor_id, self.product_id)
            yield hid_device
        finally:
            hid_device.close()

    @classmethod
    def supported_devices(cls) -> set[UsbDevice]:
        return {
            UsbDevice(dev) for dev in hid.enumerate() if cls._is_supported_vendor(dev)
        }

    @property
    def device_info(self) -> str:
        res = ""
        res += f"{self._dev!r}\n"
        res += f"  manufacturer: {self.manufacturer}\n"
        res += f"  product: {self.product}\n"
        res += f"  serial: {self.serial_number}\n"
        # configs = self._dev.configurations()
        # if configs:
        #     res += "  configurations:\n"
        #     for cfg in configs:
        #         res += f"  - {cfg!r}\n"
        #         intfs = cfg.interfaces()
        #         if intfs:
        #             res += "    interfaces:\n"
        #             for intf in intfs:
        #                 res += f"    - {intf!r}\n"
        return res
