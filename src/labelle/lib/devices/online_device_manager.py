from __future__ import annotations

import logging

from PyQt6 import QtCore
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget
from usb.core import NoBackendError, USBError

from labelle.lib.devices.device_manager import DeviceManager, DeviceManagerError
from labelle.lib.devices.usb_device import UsbDevice

LOG = logging.getLogger(__name__)
POSSIBLE_USB_ERRORS = (NoBackendError, USBError)


class OnlineDeviceManager(QWidget):
    _last_scan_error: DeviceManagerError | None
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
    def last_scan_error(self) -> DeviceManagerError | None:
        return self._last_scan_error

    @property
    def devices(self) -> list[UsbDevice]:
        return self._device_manager.devices
