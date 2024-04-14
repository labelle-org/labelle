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
from labelle.lib.dymo_labeler import (
    DymoLabeler,
    DymoLabelerDetectError,
    DymoLabelerPrintError,
)
from labelle.lib.logger import configure_logging, is_verbose_env_vars, set_not_verbose
from labelle.lib.render_engines import RenderContext
from labelle.lib.utils import system_run

from .q_dymo_labels_list import QDymoLabelList

LOG = logging.getLogger(__name__)


class DymoPrintWindow(QWidget):
    label_bitmap_to_print: Optional[Image.Image]
    dymo_labeler: DymoLabeler
    render_context: RenderContext
    tape_size_mm: QComboBox

    def __init__(self):
        super().__init__()
        self.label_bitmap_to_print = None
        self.detected_device = None

        self.window_layout = QVBoxLayout()

        self.label_list = QDymoLabelList()
        self.label_render = QLabel()
        self.error_label = QLabel()
        self.print_button = QPushButton()
        self.horizontal_margin_mm = QSpinBox()
        self.tape_size_mm = QComboBox()
        self.foreground_color = QComboBox()
        self.background_color = QComboBox()
        self.min_label_width_mm = QSpinBox()
        self.justify = QComboBox()
        self.preview_show_margins = QCheckBox()
        self.last_error = None

        self.init_elements()
        self.init_timers()
        self.init_connections()
        self.init_layout()

        self.label_list.render_label()

    def init_elements(self):
        self.setWindowTitle("Labelle GUI")
        self.setWindowIcon(QIcon(str(ICON_DIR / "logo_small.png")))
        self.setGeometry(200, 200, 1100, 400)
        printer_icon = QIcon.fromTheme("printer")
        self.print_button.setIcon(printer_icon)
        self.print_button.setFixedSize(64, 64)
        self.print_button.setIconSize(QSize(48, 48))

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        self.label_render.setGraphicsEffect(shadow)

        self.dymo_labeler = DymoLabeler()
        for tape_size_mm in self.dymo_labeler.SUPPORTED_TAPE_SIZES_MM:
            self.tape_size_mm.addItem(str(tape_size_mm), tape_size_mm)
        tape_size_index = self.dymo_labeler.SUPPORTED_TAPE_SIZES_MM.index(
            self.dymo_labeler.tape_size_mm
        )
        self.tape_size_mm.setCurrentIndex(tape_size_index)

        h_margins_mm = round(self.dymo_labeler.minimum_horizontal_margin_mm)
        self.horizontal_margin_mm.setMinimum(h_margins_mm)
        self.horizontal_margin_mm.setMaximum(100)
        self.horizontal_margin_mm.setValue(h_margins_mm)

        self.min_label_width_mm.setMinimum(h_margins_mm * 2)
        self.min_label_width_mm.setMaximum(300)
        self.justify.addItems(["center", "left", "right"])

        self.foreground_color.addItems(
            ["black", "white", "yellow", "blue", "red", "green"]
        )
        self.background_color.addItems(
            ["white", "black", "yellow", "blue", "red", "green"]
        )
        self.preview_show_margins.setChecked(False)

        self.update_params()
        self.label_list.populate()

    def init_timers(self):
        self.check_status()
        self.status_time = QTimer()
        self.status_time.timeout.connect(self.check_status)
        self.status_time.setInterval(2000)
        self.status_time.start(2000)

    def init_connections(self):
        self.horizontal_margin_mm.valueChanged.connect(self.label_list.render_label)
        self.horizontal_margin_mm.valueChanged.connect(self.update_params)
        self.tape_size_mm.currentTextChanged.connect(self.update_params)
        self.min_label_width_mm.valueChanged.connect(self.update_params)
        self.justify.currentTextChanged.connect(self.update_params)
        self.foreground_color.currentTextChanged.connect(self.update_params)
        self.background_color.currentTextChanged.connect(self.update_params)
        self.label_list.renderPrintPreviewSignal.connect(self.update_preview_render)
        self.label_list.renderPrintPayloadSignal.connect(self.update_print_render)
        self.print_button.clicked.connect(self.print_label)
        self.preview_show_margins.stateChanged.connect(self.update_params)

    def init_layout(self):
        settings_widget = QToolBar(self)
        settings_widget.addWidget(QLabel("Margin [mm]:"))
        settings_widget.addWidget(self.horizontal_margin_mm)
        settings_widget.addSeparator()
        settings_widget.addWidget(QLabel("Tape Size [mm]:"))
        settings_widget.addWidget(self.tape_size_mm)
        settings_widget.addSeparator()
        settings_widget.addWidget(QLabel("Min Label Length [mm]:"))
        settings_widget.addWidget(self.min_label_width_mm)
        settings_widget.addSeparator()
        settings_widget.addWidget(QLabel("Justify:"))
        settings_widget.addWidget(self.justify)
        settings_widget.addSeparator()
        settings_widget.addWidget(QLabel("Tape Colors: "))
        settings_widget.addWidget(self.foreground_color)
        settings_widget.addWidget(QLabel(" on "))
        settings_widget.addWidget(self.background_color)
        settings_widget.addWidget(QLabel("Show margins:"))
        settings_widget.addWidget(self.preview_show_margins)

        render_widget = QWidget(self)
        label_render_widget = QWidget(render_widget)
        print_render_widget = QWidget(render_widget)

        render_layout = QHBoxLayout(render_widget)
        label_render_layout = QVBoxLayout(label_render_widget)
        print_render_layout = QVBoxLayout(print_render_widget)
        label_render_layout.addWidget(
            self.label_render, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        print_render_layout.addWidget(
            self.print_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        print_render_layout.addWidget(
            self.error_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        render_layout.addWidget(
            label_render_widget, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        render_layout.addWidget(
            print_render_widget, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )

        self.window_layout.addWidget(settings_widget)
        self.window_layout.addWidget(self.label_list)
        self.window_layout.addWidget(render_widget)
        self.setLayout(self.window_layout)

    def update_params(self):
        justify: Literal["left", "center", "right"] = self.justify.currentText()
        horizontal_margin_mm: float = self.horizontal_margin_mm.value()
        min_label_width_mm: float = self.min_label_width_mm.value()
        tape_size_mm: int = self.tape_size_mm.currentData()

        self.dymo_labeler.tape_size_mm = tape_size_mm

        # Update render context
        self.render_context = RenderContext(
            foreground_color=self.foreground_color.currentText(),
            background_color=self.background_color.currentText(),
            height_px=self.dymo_labeler.height_px,
            preview_show_margins=self.preview_show_margins.isChecked(),
        )

        self.label_list.update_params(
            dymo_labeler=self.dymo_labeler,
            h_margin_mm=horizontal_margin_mm,
            min_label_width_mm=min_label_width_mm,
            render_context=self.render_context,
            justify=justify,
        )

    def update_preview_render(self, preview_bitmap):
        qim = ImageQt.ImageQt(preview_bitmap)
        q_image = QPixmap.fromImage(qim)
        self.label_render.setPixmap(q_image)
        self.label_render.adjustSize()

    def update_print_render(self, label_bitmap_to_print):
        self.label_bitmap_to_print = label_bitmap_to_print

    def print_label(self):
        try:
            if self.label_bitmap_to_print is None:
                raise RuntimeError("No label to print! Call update_label_render first.")
            self.dymo_labeler.print(self.label_bitmap_to_print)
        except DymoLabelerPrintError as err:
            crash_msg_box(self, "Printing Failed!", err)

    def check_status(self):
        self.error_label.setText("")
        try:
            self.dymo_labeler.detect()
            is_enabled = True
        except DymoLabelerDetectError as e:
            error = str(e)
            if self.last_error != error:
                self.last_error = error
                LOG.error(error)
            self.error_label.setText(error)
            is_enabled = False
        self.print_button.setEnabled(is_enabled)
        self.print_button.setCursor(
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
        window = DymoPrintWindow()
        window.show()
        sys.exit(app.exec())
