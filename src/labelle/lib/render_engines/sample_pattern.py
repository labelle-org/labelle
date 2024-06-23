from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFont

from labelle.lib.font_config import get_font_path
from labelle.lib.render_engines import RenderContext, RenderEngine
from labelle.lib.render_engines.horizontally_combined import (
    HorizontallyCombinedRenderEngine,
)
from labelle.lib.utils import draw_image

FONT_SIZE_PX = 12


class SamplePatternRenderEngine(HorizontallyCombinedRenderEngine):
    def __init__(self, height: int = 100):
        four_horizontal_lines_top_and_bottom = (
            _make_staggered_horizontal_lines_top_bottom(
                num_lines=4, width=40, height=height
            )
        )
        vertical_lines = _make_vertical_lines(num_lines=5, height=height)
        fine_checkerboard_pattern = _make_fine_checkerboard_pattern(
            width=12, height=height
        )
        solid_black = _make_solid_black(width=12, height=height)
        dyadic_checkerboard_pattern = _make_dyadic_checkerboard_pattern(height=height)

        bitmaps = [
            four_horizontal_lines_top_and_bottom,
            vertical_lines,
            fine_checkerboard_pattern,
            solid_black,
            dyadic_checkerboard_pattern,
            four_horizontal_lines_top_and_bottom,
        ]
        render_engines = [_ImageRenderEngine(bitmap) for bitmap in bitmaps]
        super().__init__(render_engines=render_engines, padding=0)


class _ImageRenderEngine(RenderEngine):
    def __init__(self, image: Image.Image):
        super().__init__()
        self.image = image

    def render(self, _: RenderContext) -> Image.Image:
        return self.image


def _make_vertical_lines(*, num_lines: int, height: int) -> Image.Image:
    width = 2 * num_lines - 1
    image = Image.new("1", (width, height))
    for x in range(0, width, 2):
        for y in range(height):
            image.putpixel((x, y), 1)
    return image


def _make_staggered_horizontal_lines_top_bottom(
    *, num_lines: int, width: int, height: int
) -> Image.Image:
    image = Image.new("1", (40, height))
    # top
    for y0 in range(0, 2 * num_lines, 2):
        for x in range(width):
            y = y0 if x < width / 2 else y0 + 1
            image.putpixel((x, y), 1)
    # bottom
    for y0 in range(height - 2 * num_lines, height, 2):
        for x in range(40):
            y = y0 + 1 if x < width / 2 else y0
            image.putpixel((x, y), 1)
    # draw height
    font_path = get_font_path(style="regular")
    font = ImageFont.truetype(str(font_path), FONT_SIZE_PX)
    with draw_image(image) as draw:
        assert isinstance(draw, ImageDraw.ImageDraw)
        text = f"h={height}"
        _left, _top, _right, text_height = font.getbbox(text)
        y = (height - text_height) // 2
        X_OFFSET = 3
        draw.text((X_OFFSET, y), text, font=font, fill=1)
    return image


def _make_fine_checkerboard_pattern(*, width: int, height: int) -> Image.Image:
    image = Image.new("1", (width, height))
    for x in range(0, width):
        for y in range(0, height):
            if (x + y) % 2 == 0:
                image.putpixel((x, y), 1)
    return image


def _make_dyadic_checkerboard_pattern(*, height: int) -> Image.Image:
    font_path = get_font_path(style="regular")
    font = ImageFont.truetype(str(font_path), FONT_SIZE_PX)
    _left, _top, _right, font_height = font.getbbox("0123456789")
    MARGIN_BELOW = 3  # One pixel above plus two pixels below the text.

    # Font block size is the first power of two greater than the required height.
    log_font_block_size = math.ceil(math.log2(font_height + MARGIN_BELOW))
    font_block_size = 2**log_font_block_size

    required_text_width = _get_required_text_width(
        font=font, height=height, log_font_block_size=log_font_block_size
    )
    text_x_offset = log_font_block_size * font_block_size
    image_width = text_x_offset + required_text_width + 2

    image = Image.new("1", (image_width, height))

    # Draw text
    for yc in range(font_block_size, height + 1, font_block_size):
        text = str(yc)
        y = height - yc - 1
        with draw_image(image) as draw:
            assert isinstance(draw, ImageDraw.ImageDraw)
            draw.text((text_x_offset + 1, y + 2), text, font=font, fill=1)

    # Draw checkerboard pattern
    for yc in range(0, height):
        y = height - yc - 1
        for x in range(image_width):
            x0 = min(x // font_block_size, log_font_block_size)
            # Get the x0-th bit of yc
            if (yc >> x0) & 1 == 0:
                if image.getpixel((x, y)) == 1:
                    image.putpixel((x, y), 0)
                else:
                    image.putpixel((x, y), 1)
    return image


def _get_required_text_width(
    *, font: ImageFont.FreeTypeFont, height: int, log_font_block_size: int
) -> int:
    font_block_size = 2**log_font_block_size
    required_text_width = 0
    for yc in range(font_block_size, height + 1, font_block_size):
        text = str(yc)
        _left, _top, text_width, _bottom = font.getbbox(text)
        required_text_width = max(text_width, required_text_width)
    return required_text_width


def _make_solid_black(*, width: int, height: int) -> Image.Image:
    return Image.new("1", (width, height), color=1)
