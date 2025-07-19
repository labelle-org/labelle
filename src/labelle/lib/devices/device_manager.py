from __future__ import annotations

import logging

from usb.core import NoBackendError, USBError

from labelle.lib.constants import (
    SUPPORTED_PRODUCTS,
    UNCONFIRMED_MESSAGE,
)
from labelle.lib.devices.device import Device
from labelle.lib.devices.usb_device import UsbDevice

LOG = logging.getLogger(__name__)
POSSIBLE_DEVICE_ERRORS = (NoBackendError, USBError)


class DeviceManagerError(RuntimeError):
    pass


class DeviceManagerNoDevices(DeviceManagerError):
    pass


class DeviceManager:
    _devices: dict[str, Device]

    def __init__(self) -> None:
        self._devices = {}

    def scan(self) -> bool:
        prev = self._devices
        try:
            cur = {dev.hash: dev for dev in Device.supported_devices() if dev.hash}
        except POSSIBLE_DEVICE_ERRORS as e:
            self._devices.clear()
            raise DeviceManagerError(f"Failed scanning devices: {e}") from e
        if len(cur) == 0:
            self._devices.clear()
            raise DeviceManagerNoDevices("No supported devices found")

        prev_set = set(prev)
        cur_set = set(cur)

        for dev in prev_set - cur_set:
            self._devices.pop(dev)
        for dev in cur_set - prev_set:
            self._devices[dev] = cur[dev]

        changed = prev_set != cur_set
        return changed

    @property
    def devices(self) -> list[Device]:
        try:
            return sorted(self._devices.values(), key=lambda dev: dev.hash)
        except POSSIBLE_DEVICE_ERRORS:
            return []

    def matching_devices(self, patterns: list[str] | None) -> list[Device]:
        try:
            matching = filter(
                lambda dev: dev.is_match(patterns), self._devices.values()
            )
            return sorted(matching, key=lambda dev: dev.hash)
        except POSSIBLE_DEVICE_ERRORS:
            return []

    def find_and_select_device(self, patterns: list[str] | None = None) -> Device:
        devices = [
            device for device in self.matching_devices(patterns) if device.is_supported
        ]
        if len(devices) == 0:
            raise DeviceManagerError("No matching devices found")
        if len(devices) > 1:
            LOG.debug("Found multiple matching Dymo devices. Using first device")
        else:
            LOG.debug("Found single device")
        for dev in devices:
            LOG.debug(dev.device_info)
        dev = devices[0]
        if dev.is_supported and type(dev) is UsbDevice:
            msg = f"Recognized device as {SUPPORTED_PRODUCTS[dev.id_product]}"
        elif dev.is_supported:
            msg = f"Recognized device as {dev.product}"
        elif type(dev) is UsbDevice:
            msg = f"Unrecognized device: {hex(dev.id_product)}. {UNCONFIRMED_MESSAGE}"
        else:
            msg = f"Unrecognized device: {dev.product}"
        LOG.debug(msg)
        return dev
