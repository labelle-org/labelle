import logging
import sys
from typing import Optional

from PIL import Image
from PyQt6 import QtCore
from PyQt6.QtCore import QCommandLineOption, QCommandLineParser
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QWidget

from labelle.gui.common import crash_msg_box
from labelle.gui.q_actions import QActions
from labelle.gui.q_device_selector import QDeviceSelector
from labelle.gui.q_labels_list import QLabelList
from labelle.gui.q_render import QRender
from labelle.gui.q_settings_toolbar import QSettingsToolbar, Settings
from labelle.lib.constants import ICON_DIR
from labelle.lib.devices.device_manager import DeviceManager
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
    _render_widget: QWidget

    def __init__(self):
        super().__init__()
        self._label_bitmap_to_print = None
        self._detected_device = None

        self._window_layout = QVBoxLayout()

        self._device_selector = QDeviceSelector(self)
        self._label_list = QLabelList()
        self._render = QRender(self)
        self._actions = QActions(self)
        self._settings_toolbar = QSettingsToolbar(self)
        self._render_widget = QWidget(self)

        self._init_elements()
        self._init_connections()
        self._init_layout()

        self._device_selector.repopulate()
        self._settings_toolbar.on_settings_changed()
        self._label_list.populate()
        self._label_list.render_label()

    def _init_elements(self):
        self.setWindowTitle("Labelle GUI")
        self.setWindowIcon(QIcon(str(ICON_DIR / "logo_small.png")))
        self.setGeometry(200, 200, 1100, 400)

        self._device_manager = DeviceManager()
        self._dymo_labeler = DymoLabeler()
        self._settings_toolbar.update_labeler_context(
            supported_tape_sizes=self._dymo_labeler.SUPPORTED_TAPE_SIZES_MM,
            installed_tape_size=self._dymo_labeler.tape_size_mm,
            minimum_horizontal_margin_mm=self._dymo_labeler.minimum_horizontal_margin_mm,
        )

    def _init_connections(self):
        self._label_list.renderPrintPreviewSignal.connect(self._update_preview_render)
        self._label_list.renderPrintPayloadSignal.connect(self._update_print_render)
        self._actions.print_label_signal.connect(self._on_print_label)
        self._settings_toolbar.settings_changed_signal.connect(
            self._on_settings_changed
        )
        self._device_selector.selectedDeviceChangedSignal.connect(
            self._on_device_selected
        )

    def _init_layout(self):
        self._actions.setParent(self._render_widget)
        self._render.setParent(self._render_widget)

        render_layout = QHBoxLayout(self._render_widget)
        render_layout.addWidget(
            self._render, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        render_layout.addWidget(
            self._actions, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )

        self._window_layout.addWidget(self._device_selector)
        self._window_layout.addWidget(self._settings_toolbar)
        self._window_layout.addWidget(self._label_list)
        self._window_layout.addWidget(self._render_widget)
        self.setLayout(self._window_layout)

    def _on_settings_changed(self, settings: Settings):
        assert self._dymo_labeler is not None
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

        is_ready = self._dymo_labeler.is_ready
        self._settings_toolbar.setEnabled(is_ready)
        self._label_list.setEnabled(is_ready)
        self._render_widget.setEnabled(is_ready)

    def _update_preview_render(self, preview_bitmap):
        self._render.update_preview_render(preview_bitmap)

    def _update_print_render(self, label_bitmap_to_print):
        self._label_bitmap_to_print = label_bitmap_to_print

    def _on_print_label(self):
        try:
            if self._label_bitmap_to_print is None:
                raise RuntimeError("No label to print! Call update_label_render first.")
            assert self._dymo_labeler is not None
            self._dymo_labeler.print(self._label_bitmap_to_print)
        except DymoLabelerPrintError as err:
            crash_msg_box(self, "Printing Failed!", err)

    def _on_device_selected(self):
        self._dymo_labeler.device = self._device_selector.selected_device
        self._settings_toolbar.on_settings_changed()


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
