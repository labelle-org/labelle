import logging
from typing import Optional

from PIL import Image
from PyQt6 import QtCore
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem, QMenu

from labelle.gui.common import crash_msg_box
from labelle.gui.q_label_widgets import (
    BarcodeDymoLabelWidget,
    EmptyRenderEngine,
    ImageDymoLabelWidget,
    QrDymoLabelWidget,
    TextDymoLabelWidget,
)
from labelle.lib.constants import Direction
from labelle.lib.devices.dymo_labeler import DymoLabeler
from labelle.lib.render_engines import (
    HorizontallyCombinedRenderEngine,
    PrintPayloadRenderEngine,
    PrintPreviewRenderEngine,
    RenderContext,
)
from labelle.lib.render_engines.render_engine import (
    RenderEngineException,
)
from labelle.lib.utils import mm_to_px

LOG = logging.getLogger(__name__)


class QLabelList(QListWidget):
    """A custom QListWidget for displaying and managing Dymo label widgets.

    Args:
    ----
        render_context (RenderContext): The render context to use for rendering the
        label.
        parent (QWidget): The parent widget of this QListWidget.

    Attributes:
    ----------
        renderPrintPreviewSignal (QtCore.pyqtSignal): A signal emitted when the preview
            is rendered.
        renderPrintPayloadSignal (QtCore.pyqtSignal): A signal emitted when the print
            payload is rendered.
        render_context (RenderContext): The render context used for rendering the label.

    Methods:
    -------
        __init__(self, render_context, parent=None): Initializes the QListWidget
            with the given render context and parent.
        dropEvent(self, e) -> None: Overrides the default drop event to update
            the label rendering.
        update_render_engine(self, render_engine): Updates the render context used
            for rendering the label.
        render_preview(self): Renders the payload using the current render context and
            emits the renderPrintPreviewSignal.
        render_print(self): Renders the print payload using the current render context
            and emits the renderPrintPayloadSignal.
        render_label(self): Renders the both preview and print payloads using the
            current render context and emits the corresponding signals.
        contextMenuEvent(self, event): Overrides the default context menu event to
            add or delete label widgets.

    """

    renderPrintPreviewSignal = QtCore.pyqtSignal(
        Image.Image, name="renderPrintPreviewSignal"
    )
    renderPrintPayloadSignal = QtCore.pyqtSignal(
        Image.Image, name="renderPrintPayloadSignal"
    )
    render_context: Optional[RenderContext]
    itemWidget: TextDymoLabelWidget
    dymo_labeler: Optional[DymoLabeler]
    h_margin_mm: float
    min_label_width_mm: Optional[float]
    justify: Direction

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dymo_labeler = None
        self.h_margin_mm = 0.0
        self.min_label_width_mm = None
        self.justify = Direction.CENTER
        self.render_context = None
        self.setAlternatingRowColors(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

    def populate(self):
        assert self.render_context is not None
        for item_widget in [TextDymoLabelWidget(self.render_context)]:
            item = QListWidgetItem(self)
            item.setSizeHint(item_widget.sizeHint())
            self.addItem(item)
            self.setItemWidget(item, item_widget)
            item_widget.itemRenderSignal.connect(self.render_label)

    def dropEvent(self, e) -> None:
        """Override the default drop event to update the label rendering.

        Args:
        ----
            e (QDropEvent): The drop event.

        """
        super().dropEvent(e)
        self.render_label()

    def update_params(
        self,
        dymo_labeler: DymoLabeler,
        h_margin_mm: float,
        min_label_width_mm: float,
        render_context: RenderContext,
        justify: Direction = Direction.CENTER,
    ):
        """Update the render context used for rendering the label.

        Args:
        ----
            dymo_labeler: an instance of DymoLabeler object
            h_margin_mm: horizontal margin [mm]
            min_label_width_mm: minimum label width [mm]
            render_context (RenderContext): The new render context to use.
            justify: justification [left,center, right]

        """
        self.dymo_labeler = dymo_labeler
        self.h_margin_mm = h_margin_mm
        self.min_label_width_mm = min_label_width_mm
        self.justify = justify
        self.render_context = render_context
        for i in range(self.count()):
            item_widget = self.itemWidget(self.item(i))
            item_widget.render_context = render_context
        self.render_label()

    @property
    def _payload_render_engine(self):
        render_engines = []
        for i in range(self.count()):
            item = self.item(i)
            item_widget = self.itemWidget(self.item(i))
            if item_widget and item:
                item.setSizeHint(item_widget.sizeHint())
                render_engines.append(item_widget.render_engine)
        return HorizontallyCombinedRenderEngine(render_engines=render_engines)

    def render_preview(self):
        assert self.dymo_labeler is not None
        assert self.render_context is not None
        render_engine = PrintPreviewRenderEngine(
            render_engine=self._payload_render_engine,
            justify=self.justify,
            visible_horizontal_margin_px=mm_to_px(self.h_margin_mm),
            labeler_margin_px=self.dymo_labeler.labeler_margin_px,
            max_width_px=None,
            min_width_px=mm_to_px(self.min_label_width_mm),
        )
        try:
            bitmap = render_engine.render(self.render_context)
        except RenderEngineException as err:
            crash_msg_box(self, "Render Engine Failed!", err)
            bitmap = EmptyRenderEngine().render(self.render_context)

        self.renderPrintPreviewSignal.emit(bitmap)

    def render_print(self):
        assert self.dymo_labeler is not None
        assert self.render_context is not None
        render_engine = PrintPayloadRenderEngine(
            render_engine=self._payload_render_engine,
            justify=self.justify,
            visible_horizontal_margin_px=mm_to_px(self.h_margin_mm),
            labeler_margin_px=self.dymo_labeler.labeler_margin_px,
            max_width_px=None,
            min_width_px=mm_to_px(self.min_label_width_mm),
        )
        try:
            bitmap, _ = render_engine.render_with_meta(self.render_context)
        except RenderEngineException as err:
            crash_msg_box(self, "Render Engine Failed!", err)
            bitmap = EmptyRenderEngine().render(self.render_context)

        self.renderPrintPayloadSignal.emit(bitmap)

    def render_label(self):
        self.render_preview()
        self.render_print()

    def contextMenuEvent(self, event):
        """Override the default context menu event to add or delete label widgets.

        Args:
        ----
            event (QContextMenuEvent): The context menu event.

        """
        assert self.render_context is not None
        contextMenu = QMenu(self)
        add_text: Optional[QAction] = contextMenu.addAction("Add Text")
        add_qr: Optional[QAction] = contextMenu.addAction("Add QR")
        add_barcode: Optional[QAction] = contextMenu.addAction("Add Barcode")
        add_img: Optional[QAction] = contextMenu.addAction("Add Image")
        delete: Optional[QAction] = contextMenu.addAction("Delete")
        menu_click = contextMenu.exec(event.globalPos())

        if menu_click == add_text:
            item = QListWidgetItem(self)
            item_widget = TextDymoLabelWidget(self.render_context)
            item.setSizeHint(item_widget.sizeHint())
            self.addItem(item)
            self.setItemWidget(item, item_widget)
            item_widget.itemRenderSignal.connect(self.render_label)

        if menu_click == add_qr:
            item = QListWidgetItem(self)
            item_widget = QrDymoLabelWidget(self.render_context)
            item.setSizeHint(item_widget.sizeHint())
            self.addItem(item)
            self.setItemWidget(item, item_widget)
            item_widget.itemRenderSignal.connect(self.render_label)

        if menu_click == add_barcode:
            item = QListWidgetItem(self)
            item_widget = BarcodeDymoLabelWidget(self.render_context)
            item.setSizeHint(item_widget.sizeHint())
            self.addItem(item)
            self.setItemWidget(item, item_widget)
            item_widget.itemRenderSignal.connect(self.render_label)

        if menu_click == add_img:
            item = QListWidgetItem(self)
            item_widget = ImageDymoLabelWidget(self.render_context)
            item.setSizeHint(item_widget.sizeHint())
            self.addItem(item)
            self.setItemWidget(item, item_widget)
            item_widget.itemRenderSignal.connect(self.render_label)
        if menu_click == delete:
            try:
                item_to_delete = self.itemAt(event.pos())
                self.takeItem(self.indexFromItem(item_to_delete).row())  # self.update()
            except Exception as e:  # noqa: BLE001
                LOG.warning(f"No item selected {e}")
        self.render_label()
