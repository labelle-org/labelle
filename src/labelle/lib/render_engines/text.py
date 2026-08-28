from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFont

from labelle.lib.constants import Direction
from labelle.lib.render_engines.render_context import RenderContext
from labelle.lib.render_engines.render_engine import RenderEngine
from labelle.lib.utils import draw_image


class TextRenderEngine(RenderEngine):
    def __init__(
        self,
        text_lines: str | list[str],
        font_file_name: Path | str,
        frame_width_px: int = 0,
        font_size_ratio: float = 0.9,
        align: Direction = Direction.CENTER,
    ):
        if isinstance(text_lines, str):
            text_lines = [text_lines]

        if len(text_lines) == 0:
            text_lines = [" "]

        self.text_lines = text_lines
        self.font_file_name = font_file_name
        self.frame_width_px = frame_width_px
        self.font_size_ratio = font_size_ratio
        self.align = align

        super().__init__()

    def render(self, context: RenderContext) -> Image.Image:
        height_px = context.height_px
        line_height = float(height_px) / len(self.text_lines)
        font_size_px = int(round(line_height * self.font_size_ratio))

        font_offset_px = int((line_height - font_size_px) / 2)
        if self.frame_width_px:
            frame_width_px = self.frame_width_px or min(
                self.frame_width_px, font_offset_px, 3
            )
        else:
            frame_width_px = self.frame_width_px

        font = ImageFont.truetype(str(self.font_file_name), font_size_px)
        boxes = (font.getbbox(line) for line in self.text_lines)
        line_widths = (right - left for left, _top, right, _bottom in boxes)
        label_width_px = max(line_widths) + (font_offset_px * 2)
        bitmap = Image.new("1", (label_width_px, height_px))
        with draw_image(bitmap) as draw:
            # draw frame into empty image
            if frame_width_px:
                draw.rectangle(((0, 4), (label_width_px - 1, height_px - 4)), fill=1)
                draw.rectangle(
                    (
                        (frame_width_px, 4 + frame_width_px),
                        (
                            label_width_px - (frame_width_px + 1),
                            height_px - (frame_width_px + 4),
                        ),
                    ),
                    fill=0,
                )

            # write the text into the empty image
            #
            # PIL's "mm" (middle/middle) anchor centers using the font's
            # ascent/descent line metrics, not the text's actual ink. Text
            # with no descenders (no g/j/p/q/y) then renders visibly shifted
            # toward the top of the canvas, since the reserved descender
            # space below it stays blank. Center on the real ink bounding
            # box instead so any string ends up visually centered.
            multiline_text = "\n".join(self.text_lines)
            _left, ink_top, _right, ink_bottom = draw.multiline_textbbox(
                (0, 0),
                multiline_text,
                align=self.align.value,
                anchor="la",
                font=font,
            )
            vertical_anchor_y = height_px / 2 - (ink_top + ink_bottom) / 2
            draw.multiline_text(
                (label_width_px / 2, vertical_anchor_y),
                multiline_text,
                align=self.align.value,
                anchor="ma",
                font=font,
                fill=1,
            )
        return bitmap
