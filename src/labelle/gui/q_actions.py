import logging
from typing import Optional

from PyQt6 import QtCore
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

LOG = logging.getLogger(__name__)


class QActions(QWidget):
    _error_label: QLabel
    _is_enabled: bool
    _last_error: Optional[str]
    _print_button: QPushButton

    print_label_signal = QtCore.pyqtSignal(name="printLabel")

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._error_label = QLabel()
        self._is_enabled = False
        self._last_error = None
        self._print_button = QPushButton()

        self._init_elements()
        self._init_connections()
        self._init_layout()

    def _init_elements(self):
        printer_icon = QIcon.fromTheme("printer")
        self._print_button.setIcon(printer_icon)
        self._print_button.setFixedSize(64, 64)
        self._print_button.setIconSize(QSize(48, 48))

    def _init_connections(self):
        self._print_button.clicked.connect(self._on_print_label)

    def _init_layout(self):
        layout = QVBoxLayout(self)
        layout.addWidget(
            self._print_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        layout.addWidget(
            self._error_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )

    def _on_print_label(self):
        self.print_label_signal.emit()

    def clear_error(self):
        self._error_label.setText("")
        self._last_error = None
        self._print_button.setEnabled(True)
        self._print_button.setCursor(Qt.CursorShape.ArrowCursor)

    def set_error(self, error: str):
        if self._last_error == error:
            return
        self._last_error = error
        self._error_label.setText(error)
        LOG.error(error)
        self._print_button.setDisabled(True)
        self._print_button.setCursor(Qt.CursorShape.ForbiddenCursor)
