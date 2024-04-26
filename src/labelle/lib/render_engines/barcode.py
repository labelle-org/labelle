from __future__ import annotations

import barcode as barcode_module
from PIL import Image

from labelle.lib.barcode_writer import BarcodeImageWriter
from labelle.lib.constants import DEFAULT_BARCODE_TYPE
from labelle.lib.render_engines.render_context import RenderContext
from labelle.lib.render_engines.render_engine import (
    RenderEngine,
    RenderEngineException,
)


class BarcodeRenderError(RenderEngineException):
    def __init__(self):
        msg = "Barcode render error"
        super().__init__(msg)


class BarcodeRenderEngine(RenderEngine):
    def __init__(self, content: str, barcode_type: str | None):
        super().__init__()
        self.content = content
        self.barcode_type = barcode_type or DEFAULT_BARCODE_TYPE

    def render(self, context: RenderContext) -> Image.Image:
        code = barcode_module.get(
            self.barcode_type, self.content, writer=BarcodeImageWriter()
        )
        try:
            bitmap = code.render(
                {
                    "font_size": 0,
                    "vertical_margin": 8,
                    "module_height": context.height_px - 16,
                    "module_width": 2,
                    "background": "black",
                    "foreground": "white",
                }
            )
        except BaseException as e:  # noqa
            raise BarcodeRenderError from e
        return bitmap
