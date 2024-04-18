import logging
from typing import Optional

from PIL import ImageQt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QLabel, QWidget

LOG = logging.getLogger(__name__)


class QRender(QLabel):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_elements()

    def _init_elements(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        self.setGraphicsEffect(shadow)

    def update_preview_render(self, preview_bitmap):
        qim = ImageQt.ImageQt(preview_bitmap)
        q_image = QPixmap.fromImage(qim)
        self.setPixmap(q_image)
        self.adjustSize()
