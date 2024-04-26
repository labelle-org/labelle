from __future__ import annotations

import logging
from dataclasses import dataclass

from PyQt6 import QtCore
from PyQt6.QtWidgets import QCheckBox, QComboBox, QLabel, QSpinBox, QToolBar, QWidget

from labelle.lib.constants import Direction

LOG = logging.getLogger(__name__)


FOREGROUND_COLOR__VALUES = ["black", "white", "yellow", "blue", "red", "green"]
BACKGROUND_COLOR__VALUES = ["white", "black", "yellow", "blue", "red", "green"]
HORIZONTAL_MARGIN_MM__MAX_VALUE = 100
MIN_LABEL_WIDTH_MM__MIN_VALUE = 300
PREVIEW_SHOW_MARGINS__DEFAULT_VALUE = False


@dataclass
class Settings:
    background_color: str
    foreground_color: str
    horizontal_margin_mm: float
    justify: Direction
    min_label_width_mm: float
    preview_show_margins: bool
    tape_size_mm: int


class QSettingsToolbar(QToolBar):
    settings_changed_signal = QtCore.pyqtSignal(Settings, name="settingsChangedSignal")

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._background_color = QComboBox()
        self._foreground_color = QComboBox()
        self._horizontal_margin_mm = QSpinBox()
        self._justify = QComboBox()
        self._min_label_width_mm = QSpinBox()
        self._preview_show_margins = QCheckBox()
        self._tape_size_mm = QComboBox()

        self._init_elements()
        self._init_connections()
        self._init_layout()
        self.on_settings_changed()

    def _init_elements(self):
        self._horizontal_margin_mm.setMaximum(HORIZONTAL_MARGIN_MM__MAX_VALUE)
        self._min_label_width_mm.setMaximum(MIN_LABEL_WIDTH_MM__MIN_VALUE)
        self._justify.addItems(d.value for d in Direction)
        self._foreground_color.addItems(FOREGROUND_COLOR__VALUES)
        self._background_color.addItems(BACKGROUND_COLOR__VALUES)
        self._preview_show_margins.setChecked(PREVIEW_SHOW_MARGINS__DEFAULT_VALUE)

    def update_labeler_context(
        self,
        supported_tape_sizes: tuple[int, ...],
        installed_tape_size: int,
        minimum_horizontal_margin_mm: float,
    ):
        for tape_size_mm in supported_tape_sizes:
            self._tape_size_mm.addItem(str(tape_size_mm), tape_size_mm)
        tape_size_index = supported_tape_sizes.index(installed_tape_size)
        self._tape_size_mm.setCurrentIndex(tape_size_index)

        h_margins_mm = round(minimum_horizontal_margin_mm)
        self._horizontal_margin_mm.setMinimum(h_margins_mm)
        if not self._horizontal_margin_mm.value():
            self._horizontal_margin_mm.setValue(h_margins_mm)
        self._min_label_width_mm.setMinimum(h_margins_mm * 2)

    def _init_connections(self):
        self._background_color.currentTextChanged.connect(self.on_settings_changed)
        self._foreground_color.currentTextChanged.connect(self.on_settings_changed)
        self._horizontal_margin_mm.valueChanged.connect(self.on_settings_changed)
        self._justify.currentTextChanged.connect(self.on_settings_changed)
        self._min_label_width_mm.valueChanged.connect(self.on_settings_changed)
        self._preview_show_margins.stateChanged.connect(self.on_settings_changed)
        self._tape_size_mm.currentTextChanged.connect(self.on_settings_changed)

    def _init_layout(self):
        self.addWidget(QLabel("Margin [mm]:"))
        self.addWidget(self._horizontal_margin_mm)
        self.addSeparator()
        self.addWidget(QLabel("Tape Size [mm]:"))
        self.addWidget(self._tape_size_mm)
        self.addSeparator()
        self.addWidget(QLabel("Min Label Length [mm]:"))
        self.addWidget(self._min_label_width_mm)
        self.addSeparator()
        self.addWidget(QLabel("Justify:"))
        self.addWidget(self._justify)
        self.addSeparator()
        self.addWidget(QLabel("Tape Colors: "))
        self.addWidget(self._foreground_color)
        self.addWidget(QLabel(" on "))
        self.addWidget(self._background_color)
        self.addWidget(QLabel("Show margins:"))
        self.addWidget(self._preview_show_margins)

    @property
    def settings(self):
        return Settings(
            background_color=self._background_color.currentText(),
            foreground_color=self._foreground_color.currentText(),
            horizontal_margin_mm=self._horizontal_margin_mm.value(),
            justify=Direction(self._justify.currentText()),
            min_label_width_mm=self._min_label_width_mm.value(),
            preview_show_margins=self._preview_show_margins.isChecked(),
            tape_size_mm=self._tape_size_mm.currentData(),
        )

    def on_settings_changed(self):
        self.settings_changed_signal.emit(self.settings)
