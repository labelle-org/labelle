import math

from PIL import Image, ImageDraw, ImageFont

from labelle.lib.font_config import get_font_path
from labelle.lib.render_engines import RenderContext, RenderEngine
from labelle.lib.render_engines.horizontally_combined import (
    HorizontallyCombinedRenderEngine,
)
from labelle.lib.utils import draw_image


class SamplePatternRenderEngine(HorizontallyCombinedRenderEngine):
    def __init__(self, width: int = 100):
        five_vertical_lines = Image.new("1", (9, width))
        for x in range(0, 9, 2):
            for y in range(five_vertical_lines.height):
                five_vertical_lines.putpixel((x, y), 1)

        fine_checkerboard_pattern = Image.new("1", (4, width))
        for x in range(0, 4):
            for y in range(0, width):
                if (x + y) % 2 == 0:
                    fine_checkerboard_pattern.putpixel((x, y), 1)

        dyadic_checkerboard_pattern = Image.new("1", (width, width))
        font_path = get_font_path(style="regular")
        font = ImageFont.truetype(str(font_path), 12)
        ss = 1
        while ss <= (width / 2):
            for x in range(ss - 1, 2 * ss - 1):
                for y in range(0, width):
                    if x == ss - 1 and y % ss == ss - 1:
                        _left, _top, right, bottom = font.getbbox(str(y + 1))
                        number_size_px = max(right, bottom)
                        if number_size_px <= ss:
                            with draw_image(dyadic_checkerboard_pattern) as draw:
                                assert isinstance(draw, ImageDraw.ImageDraw)
                                draw.text(
                                    (x, y - bottom), str(y + 1), font=font, fill=1
                                )
                    if (math.floor(y / ss) % 2) == 0:
                        if dyadic_checkerboard_pattern.getpixel((x, y)) == 1:
                            dyadic_checkerboard_pattern.putpixel((x, y), 0)
                        else:
                            dyadic_checkerboard_pattern.putpixel((x, y), 1)

            ss *= 2

        four_horizontal_lines_top_and_bottom = Image.new("1", (40, width))
        # top
        for y0 in range(0, 8, 2):
            for x in range(40):
                y = y0 if x < 20 else y0 + 1
                four_horizontal_lines_top_and_bottom.putpixel((x, y), 1)
        # bottom
        for y0 in range(width - 8, width, 2):
            for x in range(40):
                y = y0 + 1 if x < 20 else y0
                four_horizontal_lines_top_and_bottom.putpixel((x, y), 1)

        bitmaps = [
            four_horizontal_lines_top_and_bottom,
            five_vertical_lines,
            fine_checkerboard_pattern,
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
