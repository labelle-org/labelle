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
    def __init__(self) -> None:
        msg = "Barcode render error"
        super().__init__(msg)


class BarcodeRenderEngine(RenderEngine):
    def __init__(self, content: str, barcode_type: str | None) -> None:
        super().__init__()
        self.content = content
        self.barcode_type = barcode_type or DEFAULT_BARCODE_TYPE

    def render(self, context: RenderContext) -> Image.Image:
        if self.barcode_type == "code128" and self.content == "":
            # An exception is raised on the empty string. Since this is
            # the default code, we really don't want to trigger a popup
            # in the GUI before the user entered a barcode.
            self.content = " "
        try:
            code = barcode_module.get(
                self.barcode_type, self.content, writer=BarcodeImageWriter()
            )
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
