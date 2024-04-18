import logging
import sys
from typing import Literal, Optional

from PIL import Image, ImageQt
from PyQt6 import QtCore
from PyQt6.QtCore import QCommandLineOption, QCommandLineParser, QSize, Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from labelle.gui.common import crash_msg_box
from labelle.lib.constants import ICON_DIR
from labelle.lib.devices.device_manager import DeviceManager, DeviceManagerError
from labelle.lib.devices.dymo_labeler import (
    DymoLabeler,
    DymoLabelerPrintError,
)
from labelle.lib.env_config import is_verbose_env_vars
from labelle.lib.logger import configure_logging, set_not_verbose
from labelle.lib.render_engines import RenderContext
from labelle.lib.utils import system_run

from .q_dymo_labels_list import QDymoLabelList

LOG = logging.getLogger(__name__)


class LabelleWindow(QWidget):
    _label_bitmap_to_print: Optional[Image.Image]
    _device_manager: DeviceManager
    _dymo_labeler: DymoLabeler
    _render_context: RenderContext
    _tape_size_mm: QComboBox

    def __init__(self):
        super().__init__()
        self._label_bitmap_to_print = None
        self._detected_device = None

        self._window_layout = QVBoxLayout()

        self._label_list = QDymoLabelList()
        self._label_render = QLabel()
        self._error_label = QLabel()
        self._print_button = QPushButton()
        self._horizontal_margin_mm = QSpinBox()
        self._tape_size_mm = QComboBox()
        self._foreground_color = QComboBox()
        self._background_color = QComboBox()
        self._min_label_width_mm = QSpinBox()
        self._justify = QComboBox()
        self._preview_show_margins = QCheckBox()
        self._last_error = None

        self._init_elements()
        self._init_timers()
        self._init_connections()
        self._init_layout()

        self._label_list.render_label()

    def _init_elements(self):
        self.setWindowTitle("Labelle GUI")
        self.setWindowIcon(QIcon(str(ICON_DIR / "logo_small.png")))
        self.setGeometry(200, 200, 1100, 400)
        printer_icon = QIcon.fromTheme("printer")
        self._print_button.setIcon(printer_icon)
        self._print_button.setFixedSize(64, 64)
        self._print_button.setIconSize(QSize(48, 48))

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        self._label_render.setGraphicsEffect(shadow)

        self._device_manager = DeviceManager()
        self._dymo_labeler = DymoLabeler()
        for tape_size_mm in self._dymo_labeler.SUPPORTED_TAPE_SIZES_MM:
            self._tape_size_mm.addItem(str(tape_size_mm), tape_size_mm)
        tape_size_index = self._dymo_labeler.SUPPORTED_TAPE_SIZES_MM.index(
            self._dymo_labeler.tape_size_mm
        )
        self._tape_size_mm.setCurrentIndex(tape_size_index)

        h_margins_mm = round(self._dymo_labeler.minimum_horizontal_margin_mm)
        self._horizontal_margin_mm.setMinimum(h_margins_mm)
        self._horizontal_margin_mm.setMaximum(100)
        self._horizontal_margin_mm.setValue(h_margins_mm)

        self._min_label_width_mm.setMinimum(h_margins_mm * 2)
        self._min_label_width_mm.setMaximum(300)
        self._justify.addItems(["center", "left", "right"])

        self._foreground_color.addItems(
            ["black", "white", "yellow", "blue", "red", "green"]
        )
        self._background_color.addItems(
            ["white", "black", "yellow", "blue", "red", "green"]
        )
        self._preview_show_margins.setChecked(False)

        self._update_params()
        self._label_list.populate()

    def _init_timers(self):
        self._refresh_devices()
        self._status_time = QTimer()
        self._status_time.timeout.connect(self._refresh_devices)
        self._status_time.start(2000)

    def _init_connections(self):
        self._horizontal_margin_mm.valueChanged.connect(self._label_list.render_label)
        self._horizontal_margin_mm.valueChanged.connect(self._update_params)
        self._tape_size_mm.currentTextChanged.connect(self._update_params)
        self._min_label_width_mm.valueChanged.connect(self._update_params)
        self._justify.currentTextChanged.connect(self._update_params)
        self._foreground_color.currentTextChanged.connect(self._update_params)
        self._background_color.currentTextChanged.connect(self._update_params)
        self._label_list.renderPrintPreviewSignal.connect(self._update_preview_render)
        self._label_list.renderPrintPayloadSignal.connect(self._update_print_render)
        self._print_button.clicked.connect(self._print_label)
        self._preview_show_margins.stateChanged.connect(self._update_params)

    def _init_layout(self):
        settings_widget = QToolBar(self)
        settings_widget.addWidget(QLabel("Margin [mm]:"))
        settings_widget.addWidget(self._horizontal_margin_mm)
        settings_widget.addSeparator()
        settings_widget.addWidget(QLabel("Tape Size [mm]:"))
        settings_widget.addWidget(self._tape_size_mm)
        settings_widget.addSeparator()
        settings_widget.addWidget(QLabel("Min Label Length [mm]:"))
        settings_widget.addWidget(self._min_label_width_mm)
        settings_widget.addSeparator()
        settings_widget.addWidget(QLabel("Justify:"))
        settings_widget.addWidget(self._justify)
        settings_widget.addSeparator()
        settings_widget.addWidget(QLabel("Tape Colors: "))
        settings_widget.addWidget(self._foreground_color)
        settings_widget.addWidget(QLabel(" on "))
        settings_widget.addWidget(self._background_color)
        settings_widget.addWidget(QLabel("Show margins:"))
        settings_widget.addWidget(self._preview_show_margins)

        render_widget = QWidget(self)
        label_render_widget = QWidget(render_widget)
        print_render_widget = QWidget(render_widget)

        render_layout = QHBoxLayout(render_widget)
        label_render_layout = QVBoxLayout(label_render_widget)
        print_render_layout = QVBoxLayout(print_render_widget)
        label_render_layout.addWidget(
            self._label_render, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        print_render_layout.addWidget(
            self._print_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        print_render_layout.addWidget(
            self._error_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        render_layout.addWidget(
            label_render_widget, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        render_layout.addWidget(
            print_render_widget, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )

        self._window_layout.addWidget(settings_widget)
        self._window_layout.addWidget(self._label_list)
        self._window_layout.addWidget(render_widget)
        self.setLayout(self._window_layout)

    def _update_params(self):
        justify: Literal["left", "center", "right"] = self._justify.currentText()
        horizontal_margin_mm: float = self._horizontal_margin_mm.value()
        min_label_width_mm: float = self._min_label_width_mm.value()
        tape_size_mm: int = self._tape_size_mm.currentData()

        self._dymo_labeler.tape_size_mm = tape_size_mm

        # Update render context
        self._render_context = RenderContext(
            foreground_color=self._foreground_color.currentText(),
            background_color=self._background_color.currentText(),
            height_px=self._dymo_labeler.height_px,
            preview_show_margins=self._preview_show_margins.isChecked(),
        )

        self._label_list.update_params(
            dymo_labeler=self._dymo_labeler,
            h_margin_mm=horizontal_margin_mm,
            min_label_width_mm=min_label_width_mm,
            render_context=self._render_context,
            justify=justify,
        )

    def _update_preview_render(self, preview_bitmap):
        qim = ImageQt.ImageQt(preview_bitmap)
        q_image = QPixmap.fromImage(qim)
        self._label_render.setPixmap(q_image)
        self._label_render.adjustSize()

    def _update_print_render(self, label_bitmap_to_print):
        self._label_bitmap_to_print = label_bitmap_to_print

    def _print_label(self):
        try:
            if self._label_bitmap_to_print is None:
                raise RuntimeError("No label to print! Call update_label_render first.")
            self._dymo_labeler.print(self._label_bitmap_to_print)
        except DymoLabelerPrintError as err:
            crash_msg_box(self, "Printing Failed!", err)

    def _refresh_devices(self):
        self._error_label.setText("")
        try:
            self._device_manager.scan()
            device = self._device_manager.find_and_select_device()
            device.setup()
            self._dymo_labeler.device = device
            is_enabled = True
        except DeviceManagerError as e:
            error = str(e)
            if self._last_error != error:
                self._last_error = error
                LOG.error(error)
            self._error_label.setText(error)
            is_enabled = False
        self._print_button.setEnabled(is_enabled)
        self._print_button.setCursor(
            Qt.CursorShape.ArrowCursor if is_enabled else Qt.CursorShape.ForbiddenCursor
        )


def parse(app):
    """Parse the arguments and options of the given app object."""
    parser = QCommandLineParser()
    parser.addHelpOption()

    verbose_option = QCommandLineOption(["v", "verbose"], "Verbose output.")
    parser.addOption(verbose_option)
    parser.process(app)

    is_verbose = parser.isSet(verbose_option)
    if (not is_verbose) and (not is_verbose_env_vars()):
        # Neither the --verbose flag nor the environment variable is set.
        set_not_verbose()


def main():
    configure_logging()
    with system_run():
        app = QApplication(sys.argv)
        parse(app)
        window = LabelleWindow()
        window.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
