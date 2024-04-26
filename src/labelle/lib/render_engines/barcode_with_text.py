from __future__ import annotations

from pathlib import Path

from PIL import Image

from labelle.lib.constants import Direction
from labelle.lib.render_engines.barcode import BarcodeRenderEngine
from labelle.lib.render_engines.render_context import RenderContext
from labelle.lib.render_engines.render_engine import (
    RenderEngine,
    RenderEngineException,
)
from labelle.lib.render_engines.text import TextRenderEngine


class BarcodeWithTextRenderEngine(RenderEngine):
    TEXT_HEIGHT_SCALE_FACTOR = 0.4

    def __init__(
        self,
        content: str,
        barcode_type: str | None,
        font_file_name: Path | str,
        frame_width_px: int | None,
        font_size_ratio: float = 0.9,
        align: Direction = Direction.CENTER,
    ):
        super().__init__()
        self._barcode = BarcodeRenderEngine(content, barcode_type)
        self._text = TextRenderEngine(
            content, font_file_name, frame_width_px, font_size_ratio, align
        )
        self.align = align

    def render(self, render_context: RenderContext) -> Image.Image:
        bitmap = self._barcode.render(render_context)
        text_render_context = RenderContext(
            height_px=int(render_context.height_px * self.TEXT_HEIGHT_SCALE_FACTOR),
            foreground_color=render_context.foreground_color,
            background_color=render_context.background_color,
        )
        text_bitmap = self._text.render(text_render_context)

        # Define the x and y of the upper-left corner of the text
        # to be pasted onto the barcode
        text_offset_x = bitmap.height - text_bitmap.height - 1
        if self.align == "left":
            text_offset_y = 0
        elif self.align == "center":
            text_offset_y = bitmap.width // 2 - text_bitmap.width // 2
        elif self.align == "right":
            text_offset_y = bitmap.width - text_bitmap.width
        else:
            raise RenderEngineException(f"Invalid align value: {self.align}")

        bitmap.paste(text_bitmap, (text_offset_y, text_offset_x))
        return bitmap
