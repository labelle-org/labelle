from __future__ import annotations

import logging

from usb.core import NoBackendError, USBError

from labelle.lib.constants import (
    SUPPORTED_PRODUCTS,
    UNCONFIRMED_MESSAGE,
)
from labelle.lib.devices.usb_device import UsbDevice

LOG = logging.getLogger(__name__)
POSSIBLE_USB_ERRORS = (NoBackendError, USBError)


class DeviceManagerError(RuntimeError):
    pass


class DeviceManager:
    _devices: dict[str, UsbDevice]
    last_scan_error: DeviceManagerError | None

    def __init__(self):
        self._devices = {}
        try:
            self.scan()
            self.last_scan_error = None
        except DeviceManagerError as e:
            self.last_scan_error = e

    def scan(self):
        prev = self._devices
        try:
            cur = {dev.hash: dev for dev in UsbDevice.supported_devices() if dev.hash}
        except POSSIBLE_USB_ERRORS as e:
            raise DeviceManagerError(f"Failed scanning devices: {e}") from e

        prev_set = set(prev)
        cur_set = set(cur)

        for dev in prev_set - cur_set:
            self._devices.pop(dev)
        for dev in cur_set - prev_set:
            self._devices[dev] = cur[dev]

    @property
    def devices(self) -> list[UsbDevice]:
        try:
            return sorted(self._devices.values(), key=lambda dev: dev.hash)
        except POSSIBLE_USB_ERRORS:
            return []

    def find_and_select_device(self) -> UsbDevice:
        devices = [device for device in self.devices if device.is_supported]
        if len(devices) == 0:
            raise DeviceManagerError("No devices found")
        if len(devices) > 1:
            LOG.debug("Found multiple Dymo devices. Using first device")
        else:
            LOG.debug("Found single device")
        for dev in devices:
            LOG.debug(dev.device_info)
        dev = devices[0]
        if dev.is_supported:
            msg = f"Recognized device as {SUPPORTED_PRODUCTS[dev.id_product]}"
        else:
            msg = f"Unrecognized device: {hex(dev.id_product)}. {UNCONFIRMED_MESSAGE}"
        LOG.debug(msg)
        return dev
