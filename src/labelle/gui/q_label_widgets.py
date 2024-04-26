from pathlib import Path
from typing import Optional

from PyQt6 import QtCore
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from labelle.gui.common import crash_msg_box
from labelle.lib.constants import ICON_DIR, BarcodeType, Direction
from labelle.lib.env_config import is_dev_mode_no_margins
from labelle.lib.font_config import get_available_fonts
from labelle.lib.render_engines import (
    BarcodeRenderEngine,
    BarcodeWithTextRenderEngine,
    EmptyRenderEngine,
    NoContentError,
    NoPictureFilePath,
    PictureRenderEngine,
    QrRenderEngine,
    RenderContext,
    RenderEngine,
    TextRenderEngine,
)
from labelle.lib.render_engines.render_engine import RenderEngineException


class FontStyle(QComboBox):
    def __init__(self):
        super().__init__()
        # Populate font_style
        for font_path in get_available_fonts():
            name = font_path.stem
            absolute_path = font_path.absolute()
            self.addItem(name, absolute_path)
            self.setCurrentText("Carlito-Regular")


class BaseLabelWidget(QWidget):
    """A base class for creating Dymo label widgets.

    Signals:
    --------
    itemRenderSignal : PyQtSignal
        Signal emitted when the content of the label is changed.

    Methods
    -------
    content_changed()
        Emits the itemRenderSignal when the content of the label is changed.
    render_label()
        Abstract method to be implemented by subclasses for rendering the label.

    """

    render_context: RenderContext

    itemRenderSignal = QtCore.pyqtSignal(name="itemRenderSignal")

    def content_changed(self):
        """Emit the itemRenderSignal when the content of the label is changed."""
        self.itemRenderSignal.emit()

    @property
    def render_engine_impl(self):
        """Abstract method for getting the render engine of the label."""
        pass

    @property
    def render_engine(self):
        try:
            return self.render_engine_impl
        except RenderEngineException as err:
            crash_msg_box(self, "Render Engine Failed!", err)
            return EmptyRenderEngine()


class TextDymoLabelWidget(BaseLabelWidget):
    """A widget for rendering text on a Dymo label.

    Args:
    ----
        render_context (RenderContext): The rendering context to use.
        parent (QWidget): The parent widget of this widget.

    Attributes:
    ----------
        render_context (RenderContext): The rendering context used by this widget.
        label (QPlainTextEdit): The text label to be rendered on the Dymo label.
        font_style (FontStyle): The font style selection dropdown.
        font_size (QSpinBox): The font size selection spinner.
        frame_width_px (QSpinBox): The frame width selection spinner.
    Signals:
        itemRenderSignal: A signal emitted when the content of the label changes.

    """

    align: QComboBox
    label: QPlainTextEdit
    font_style: FontStyle
    font_size: QSpinBox
    frame_width_px: QSpinBox

    def __init__(self, render_context: RenderContext, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.render_context = render_context

        default_label_text = "." if is_dev_mode_no_margins() else "text"
        self.label = QPlainTextEdit(default_label_text)
        self.label.setFixedHeight(15 * (len(self.label.toPlainText().splitlines()) + 2))
        self.setFixedHeight(self.label.height() + 10)
        self.font_style = FontStyle()
        self.font_size = QSpinBox()
        self.font_size.setMaximum(150)
        self.font_size.setMinimum(0)
        self.font_size.setSingleStep(1)
        self.font_size.setValue(90)
        self.frame_width_px = QSpinBox()
        self.align = QComboBox()

        self.align.addItems(["left", "center", "right"])

        layout = QHBoxLayout()
        item_icon = QLabel()
        item_icon.setPixmap(QIcon(str(ICON_DIR / "txt_icon.png")).pixmap(32, 32))
        item_icon.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(item_icon)
        layout.addWidget(self.label)
        layout.addWidget(QLabel("Font:"))
        layout.addWidget(self.font_style)
        layout.addWidget(QLabel("Size [%]:"))
        layout.addWidget(self.font_size)
        layout.addWidget(QLabel("Frame Width:"))
        layout.addWidget(self.frame_width_px)
        layout.addWidget(QLabel("Alignment:"))
        layout.addWidget(self.align)
        self.label.textChanged.connect(self.content_changed)
        self.frame_width_px.valueChanged.connect(self.content_changed)
        self.font_size.valueChanged.connect(self.content_changed)
        self.font_style.currentTextChanged.connect(self.content_changed)
        self.align.currentTextChanged.connect(self.content_changed)
        self.setLayout(layout)

    def content_changed(self):
        """Manage changes to the label contents.

        In particular, update the height of the label and emit the itemRenderSignal
        when the content of the label changes.
        """
        self.label.setFixedHeight(15 * (len(self.label.toPlainText().splitlines()) + 2))
        self.setFixedHeight(self.label.height() + 10)
        self.itemRenderSignal.emit()

    @property
    def render_engine_impl(self):
        """Get the render engine for the text label using the current settings.

        Returns
        -------
            TextRenderEngine: The rendered engine.

        """
        selected_alignment = Direction(self.align.currentText())
        return TextRenderEngine(
            text_lines=self.label.toPlainText().splitlines(),
            font_file_name=self.font_style.currentData(),
            frame_width_px=self.frame_width_px.value(),
            font_size_ratio=self.font_size.value() / 100.0,
            align=selected_alignment,
        )


class QrDymoLabelWidget(BaseLabelWidget):
    """A widget for rendering QR codes on Dymo labels.

    Args:
    ----
        render_context (RenderContext): The render context to use for rendering
            the QR code.
        parent (QWidget, optional): The parent widget. Defaults to None.

    """

    def __init__(self, render_context, parent=None):
        """Initialize the QrDymoLabelWidget.

        Args:
        ----
            render_context (RenderContext): The render context to use for rendering
                the QR code.
            parent (QWidget, optional): The parent widget. Defaults to None.

        """
        super().__init__(parent)
        self.render_context = render_context

        self.label = QLineEdit("")
        layout = QHBoxLayout()
        item_icon = QLabel()
        item_icon.setPixmap(QIcon(str(ICON_DIR / "qr_icon.png")).pixmap(32, 32))
        item_icon.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(item_icon)
        layout.addWidget(self.label)
        self.label.textChanged.connect(self.content_changed)
        self.setLayout(layout)

    @property
    def render_engine_impl(self):
        """Get the render engine for the QR label using the current settings.

        Returns
        -------
            QrRenderEngine: The render engine.

        """
        try:
            return QrRenderEngine(content=self.label.text())
        except NoContentError:
            return EmptyRenderEngine()


class BarcodeDymoLabelWidget(BaseLabelWidget):
    """A widget for rendering barcode labels using the Dymo label printer.

    Args:
    ----
        render_context (RenderContext): An instance of the RenderContext class.
        parent (QWidget): The parent widget of this widget.

    Attributes:
    ----------
        render_context (RenderContext): An instance of the RenderContext class.
        label (QLineEdit): A QLineEdit widget for entering the content of the
            barcode label.
        Type (QComboBox): A QComboBox widget for selecting the type of barcode
            to render.
        font_style (FontStyle): The font style selection dropdown.
        font_size (QSpinBox): The font size selection spinner.
        frame_width_px (QSpinBox): The frame width selection spinner.
    Signals:
        content_changed(): Emitted when the content of the label or the selected
            barcode type changes.

    Methods:
    -------
        __init__(self, render_context, parent=None): Initializes the widget.
        render_label_impl(self): Renders the barcode label using the current content
            and barcode type.

    """

    label: QLineEdit
    barcode_type_label: QLabel
    barcode_type: QComboBox
    show_text_label: QLabel
    show_text_checkbox: QCheckBox
    font_style: FontStyle
    font_size: QSpinBox
    frame_width_px: QSpinBox
    font_label: QLabel
    size_label: QLabel
    frame_label: QLabel
    align_label: QLabel
    align: QComboBox

    def __init__(self, render_context, parent=None):
        super().__init__(parent)
        self.render_context = render_context

        self.label = QLineEdit("")

        # Hidable text fields and their labels
        self.font_label = QLabel("Font:")
        self.font_style = FontStyle()
        self.size_label = QLabel("Size [%]:")
        self.font_size = QSpinBox()
        self.font_size.setMaximum(150)
        self.font_size.setMinimum(0)
        self.font_size.setSingleStep(1)
        self.font_size.setValue(90)
        self.frame_label = QLabel("Frame Width:")
        self.frame_width_px = QSpinBox()
        self.align_label = QLabel("Alignment:")
        self.align = QComboBox()
        self.item_icon = QLabel()
        self.item_icon.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)

        self.align.addItems(["left", "center", "right"])
        # Set the default value to "center"
        self.align.setCurrentIndex(1)

        self.set_text_fields_visibility(True)

        layout = QHBoxLayout()

        self.barcode_type_label = QLabel("Type:")
        self.barcode_type = QComboBox()
        self.barcode_type.addItems(bt.value for bt in BarcodeType)

        # Checkbox for toggling text fields
        self.show_text_label = QLabel("Text:")
        self.show_text_checkbox = QCheckBox()
        self.show_text_checkbox.setChecked(True)
        self.show_text_checkbox.stateChanged.connect(
            self.toggle_text_fields_and_rerender
        )

        layout.addWidget(self.item_icon)
        layout.addWidget(self.label)
        layout.addWidget(self.barcode_type_label)
        layout.addWidget(self.barcode_type)
        layout.addWidget(self.show_text_label)
        layout.addWidget(self.show_text_checkbox)
        layout.addWidget(self.font_label)
        layout.addWidget(self.font_style)
        layout.addWidget(self.size_label)
        layout.addWidget(self.font_size)
        layout.addWidget(self.frame_label)
        layout.addWidget(self.frame_width_px)
        layout.addWidget(self.align_label)
        layout.addWidget(self.align)

        self.label.textChanged.connect(self.content_changed)
        self.frame_width_px.valueChanged.connect(self.content_changed)
        self.font_size.valueChanged.connect(self.content_changed)
        self.font_style.currentTextChanged.connect(self.content_changed)
        self.align.currentTextChanged.connect(self.content_changed)
        self.barcode_type.currentTextChanged.connect(self.content_changed)

        self.setLayout(layout)

    def set_text_fields_visibility(self, visible):
        self.font_label.setVisible(visible)
        self.font_style.setVisible(visible)
        self.size_label.setVisible(visible)
        self.font_size.setVisible(visible)
        self.frame_label.setVisible(visible)
        self.frame_width_px.setVisible(visible)
        self.align_label.setVisible(visible)
        self.align.setVisible(visible)
        if visible:
            self.item_icon.setPixmap(
                QIcon(str(ICON_DIR / "barcode_text_icon.png")).pixmap(32, 32)
            )
        else:
            self.item_icon.setPixmap(
                QIcon(str(ICON_DIR / "barcode_icon.png")).pixmap(32, 32)
            )

    def toggle_text_fields_and_rerender(self):
        is_checked = self.show_text_checkbox.isChecked()
        self.set_text_fields_visibility(is_checked)
        self.content_changed()  # Trigger rerender

    @property
    def render_engine_impl(self):
        """Get the render engine for the barcode label using the current settings.

        Returns
        -------
            RenderEngine: The rendered engine (either BarcodeRenderEngine or
            BarcodeWithTextRenderEngine).

        """
        render_engine: RenderEngine
        if self.show_text_checkbox.isChecked():
            render_engine = BarcodeWithTextRenderEngine(
                content=self.label.text(),
                barcode_type=self.barcode_type.currentText(),
                font_file_name=self.font_style.currentData(),
                frame_width_px=self.frame_width_px.value(),
                font_size_ratio=self.font_size.value() / 100.0,
                align=self.align.currentText(),
            )
        else:
            render_engine = BarcodeRenderEngine(
                content=self.label.text(),
                barcode_type=self.barcode_type.currentText(),
            )
        return render_engine


class ImageDymoLabelWidget(BaseLabelWidget):
    """A widget for rendering image-based Dymo labels.

    Args:
    ----
        context (RenderContext): The render context to use for rendering the label.
        parent (QWidget, optional): The parent widget. Defaults to None.

    """

    def __init__(self, render_context, parent=None):
        """Initialize the ImageDymoLabelWidget.

        Args:
        ----
            render_context (RenderContext): The render context to use for rendering
                the label.
            parent (QWidget, optional): The parent widget. Defaults to None.

        """
        super().__init__(parent)
        self.render_context = render_context

        self.label = QLineEdit("")
        layout = QHBoxLayout()
        item_icon = QLabel()
        item_icon.setPixmap(QIcon(str(ICON_DIR / "img_icon.png")).pixmap(32, 32))
        item_icon.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)

        button = QPushButton("Select file")
        file_dialog = QFileDialog()
        button.clicked.connect(
            lambda: self.label.setText(
                str(Path(file_dialog.getOpenFileName()[0]).absolute())
            )
        )

        layout.addWidget(item_icon)
        layout.addWidget(self.label)
        layout.addWidget(button)

        self.label.textChanged.connect(self.content_changed)
        self.setLayout(layout)

    @property
    def render_engine_impl(self):
        """Get the render engine for the image label using the current settings.

        Returns
        -------
            PictureRenderEngine: The rendered engine.

        """
        try:
            return PictureRenderEngine(picture_path=self.label.text())
        except NoPictureFilePath:
            return EmptyRenderEngine()
