from __future__ import annotations

import logging

from usb.core import NoBackendError, USBError

from labelle.lib.constants import (
    SUPPORTED_PRODUCTS,
    UNCONFIRMED_MESSAGE,
)
from labelle.lib.devices.device_config import DeviceConfig
from labelle.lib.devices.usb_device import UsbDevice

LOG = logging.getLogger(__name__)
POSSIBLE_USB_ERRORS = (NoBackendError, USBError)


class DeviceManagerError(RuntimeError):
    pass


class DeviceManagerNoDevices(DeviceManagerError):
    pass


class DeviceManager:
    _devices: dict[str, UsbDevice]

    def __init__(self) -> None:
        self._devices = {}

    def scan(self) -> bool:
        prev = self._devices
        try:
            cur = {dev.hash: dev for dev in UsbDevice.supported_devices() if dev.hash}
        except POSSIBLE_USB_ERRORS as e:
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
    def devices(self) -> list[UsbDevice]:
        try:
            return sorted(self._devices.values(), key=lambda dev: dev.hash)
        except POSSIBLE_USB_ERRORS:
            return []

    def matching_devices(self, patterns: list[str] | None) -> list[UsbDevice]:
        try:
            matching = filter(
                lambda dev: dev.is_match(patterns), self._devices.values()
            )
            return sorted(matching, key=lambda dev: dev.hash)
        except POSSIBLE_USB_ERRORS:
            return []

    def find_and_select_device(self, patterns: list[str] | None = None) -> UsbDevice:
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
        if dev.is_supported:
            foundDeviceConfig: DeviceConfig | None = get_device_config_by_id(
                dev.id_product
            )
            if foundDeviceConfig is not None:
                msg = f"Recognized device as {foundDeviceConfig.name}"
        else:
            msg = f"Unrecognized device: {hex(dev.id_product)}. {UNCONFIRMED_MESSAGE}"
        LOG.debug(msg)
        return dev


def get_device_config_by_id(idValue: int) -> DeviceConfig | None:
    """Get a labeler device config with USB ID.

    :param idValue: USB ID value
    :return: Device config, None if not found
    """
    #
    for device in SUPPORTED_PRODUCTS:
        if device.matches_device_id(idValue) is True:
            return device

    # No device config found
    return None
