import logging
import sys
from typing import Optional

from PIL import Image, ImageQt
from PyQt6 import QtCore
from PyQt6.QtCore import QCommandLineOption, QCommandLineParser, QTimer
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from labelle.gui.common import crash_msg_box
from labelle.gui.q_actions import QActions
from labelle.gui.q_dymo_labels_list import QDymoLabelList
from labelle.gui.q_settings_toolbar import QSettingsToolbar, Settings
from labelle.lib.constants import ICON_DIR
from labelle.lib.devices.device_manager import DeviceManager, DeviceManagerError
from labelle.lib.devices.dymo_labeler import DymoLabeler, DymoLabelerPrintError
from labelle.lib.env_config import is_verbose_env_vars
from labelle.lib.logger import configure_logging, set_not_verbose
from labelle.lib.render_engines import RenderContext
from labelle.lib.utils import system_run

LOG = logging.getLogger(__name__)


class LabelleWindow(QWidget):
    _label_bitmap_to_print: Optional[Image.Image]
    _device_manager: DeviceManager
    _dymo_labeler: DymoLabeler
    _render_context: RenderContext

    def __init__(self):
        super().__init__()
        self._label_bitmap_to_print = None
        self._detected_device = None

        self._window_layout = QVBoxLayout()

        self._label_list = QDymoLabelList()
        self._label_render = QLabel()
        self._actions = QActions(self)
        self._settings_toolbar = QSettingsToolbar(self)

        self._init_elements()
        self._init_timers()
        self._init_connections()
        self._init_layout()

        self._settings_toolbar.on_settings_changed()
        self._label_list.render_label()

    def _init_elements(self):
        self.setWindowTitle("Labelle GUI")
        self.setWindowIcon(QIcon(str(ICON_DIR / "logo_small.png")))
        self.setGeometry(200, 200, 1100, 400)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        self._label_render.setGraphicsEffect(shadow)

        self._device_manager = DeviceManager()
        self._dymo_labeler = DymoLabeler()
        self._settings_toolbar.update_labeler_context(
            supported_tape_sizes=self._dymo_labeler.SUPPORTED_TAPE_SIZES_MM,
            installed_tape_size=self._dymo_labeler.tape_size_mm,
            minimum_horizontal_margin_mm=self._dymo_labeler.minimum_horizontal_margin_mm,
        )

        self._label_list.populate()

    def _init_timers(self):
        self._refresh_devices()
        self._status_time = QTimer()
        self._status_time.timeout.connect(self._refresh_devices)
        self._status_time.start(2000)

    def _init_connections(self):
        self._label_list.renderPrintPreviewSignal.connect(self._update_preview_render)
        self._label_list.renderPrintPayloadSignal.connect(self._update_print_render)
        self._actions.print_label_signal.connect(self._on_print_label)
        self._settings_toolbar.settings_changed_signal.connect(
            self._on_settings_changed
        )

    def _init_layout(self):
        render_widget = QWidget(self)
        label_render_widget = QWidget(render_widget)
        self._actions.setParent(render_widget)

        render_layout = QHBoxLayout(render_widget)
        label_render_layout = QVBoxLayout(label_render_widget)
        label_render_layout.addWidget(
            self._label_render, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        render_layout.addWidget(
            label_render_widget, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        render_layout.addWidget(
            self._actions, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )

        self._window_layout.addWidget(self._settings_toolbar)
        self._window_layout.addWidget(self._label_list)
        self._window_layout.addWidget(render_widget)
        self.setLayout(self._window_layout)

    def _on_settings_changed(self, settings: Settings):
        self._dymo_labeler.tape_size_mm = settings.tape_size_mm

        # Update render context
        self._render_context = RenderContext(
            foreground_color=settings.foreground_color,
            background_color=settings.background_color,
            height_px=self._dymo_labeler.height_px,
            preview_show_margins=settings.preview_show_margins,
        )
        self._label_list.update_params(
            dymo_labeler=self._dymo_labeler,
            h_margin_mm=settings.horizontal_margin_mm,
            min_label_width_mm=settings.min_label_width_mm,
            render_context=self._render_context,
            justify=settings.justify,
        )

    def _update_preview_render(self, preview_bitmap):
        qim = ImageQt.ImageQt(preview_bitmap)
        q_image = QPixmap.fromImage(qim)
        self._label_render.setPixmap(q_image)
        self._label_render.adjustSize()

    def _update_print_render(self, label_bitmap_to_print):
        self._label_bitmap_to_print = label_bitmap_to_print

    def _on_print_label(self):
        try:
            if self._label_bitmap_to_print is None:
                raise RuntimeError("No label to print! Call update_label_render first.")
            self._dymo_labeler.print(self._label_bitmap_to_print)
        except DymoLabelerPrintError as err:
            crash_msg_box(self, "Printing Failed!", err)

    def _refresh_devices(self):
        try:
            self._device_manager.scan()
            device = self._device_manager.find_and_select_device()
            device.setup()
            self._dymo_labeler.device = device
            self._actions.clear_error()
        except DeviceManagerError as e:
            self._actions.set_error(str(e))


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
