import logging
from typing import Optional

from PyQt6 import QtCore
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget
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

    def __init__(self):
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
            raise DeviceManagerError("No supported devices found")

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


class OnlineDeviceManager(QWidget):
    _last_scan_error: Optional[DeviceManagerError]
    _status_time: QTimer
    _device_manager: DeviceManager
    last_scan_error_changed_signal = QtCore.pyqtSignal(
        name="lastScanErrorChangedSignal"
    )
    devices_changed_signal = QtCore.pyqtSignal(name="devicesChangedSignal")

    def __init__(self):
        super().__init__()
        self._device_manager = DeviceManager()
        self._last_scan_error = None
        self._init_timers()

    def _refresh_devices(self):
        prev = self._last_scan_error
        try:
            changed = self._device_manager.scan()
            self._last_scan_error = None
            if changed:
                self.devices_changed_signal.emit()
        except DeviceManagerError as e:
            self._last_scan_error = e

        if str(prev) != str(self._last_scan_error):
            self.devices_changed_signal.emit()
            self.last_scan_error_changed_signal.emit()

    def _init_timers(self):
        self._status_time = QTimer()
        self._status_time.timeout.connect(self._refresh_devices)
        self._status_time.start(2000)
        self._refresh_devices()

    @property
    def last_scan_error(self) -> Optional[DeviceManagerError]:
        return self._last_scan_error

    @property
    def devices(self) -> list[UsbDevice]:
        return self._device_manager.devices
