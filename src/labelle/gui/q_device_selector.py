from __future__ import annotations

import logging

from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QComboBox,
    QLabel,
    QToolBar,
)

from labelle.lib.devices.online_device_manager import OnlineDeviceManager
from labelle.lib.devices.usb_device import UsbDevice

LOG = logging.getLogger(__name__)


class QDeviceSelector(QToolBar):
    _device_manager: OnlineDeviceManager
    _selected_device: UsbDevice | None

    selectedDeviceChangedSignal = QtCore.pyqtSignal(name="selectedDeviceChangedSignal")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._devices = QComboBox(self)
        self._error_label = QLabel(self)

        self._selected_device = None
        self._action_devices = None
        self._action_error_label = None

        self._init_elements()
        self._init_connections()
        self._init_layout()

        self._last_scan_error_changed()
        self.selectedDeviceChangedSignal.emit()

    def _init_elements(self):
        self.device_manager = OnlineDeviceManager()

    def _init_connections(self):
        self.device_manager.devices_changed_signal.connect(self.repopulate)
        self.device_manager.last_scan_error_changed_signal.connect(
            self._last_scan_error_changed
        )
        self._devices.currentIndexChanged.connect(self._index_changed)

    def repopulate(self):
        old_hashes = {device.hash for device in self.device_manager.devices}
        self._devices.clear()
        for idx, device in enumerate(self.device_manager.devices):
            self._devices.insertItem(idx, device.product, device.hash)
            if (
                self._selected_device is not None
                and self._selected_device.hash == device.hash
            ):
                self._devices.setCurrentIndex(idx)
        valid = len(self.device_manager.devices) > 0
        if valid:
            if self._selected_device is None:
                self._index_changed(0)
        else:
            self._index_changed(-1)
        assert self._action_devices is not None
        assert self._action_error_label is not None
        self._action_devices.setVisible(valid)
        self._action_error_label.setVisible(not valid)
        new_hashes = {device.hash for device in self.device_manager.devices}
        if new_hashes != old_hashes:
            self.selectedDeviceChangedSignal.emit()

    def _index_changed(self, index):
        if index >= 0:
            self._selected_device = self.device_manager.devices[index]
        else:
            self._selected_device = None
        self.selectedDeviceChangedSignal.emit()

    def _last_scan_error_changed(self):
        last_scan_error = self.device_manager.last_scan_error or ""
        self._error_label.setText(str(last_scan_error))
        self.repopulate()

    def _init_layout(self):
        self._devices.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._action_devices = self.addWidget(self._devices)
        self._action_error_label = self.addWidget(self._error_label)

    @property
    def selected_device(self) -> UsbDevice | None:
        device = None
        if self._devices.currentIndex() >= 0:
            device = self.device_manager.devices[self._devices.currentIndex()]
        return device
