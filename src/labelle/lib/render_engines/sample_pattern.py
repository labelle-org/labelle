import math

from PIL import Image

from labelle.lib.render_engines import RenderContext, RenderEngine
from labelle.lib.render_engines.horizontally_combined import (
    HorizontallyCombinedRenderEngine,
)


class SamplePatternRenderEngine(HorizontallyCombinedRenderEngine):
    def __init__(self, width: int = 100):
        five_vertical_lines = Image.new("1", (10, width))
        for x in range(0, 9, 2):
            for y in range(five_vertical_lines.height):
                five_vertical_lines.putpixel((x, y), 1)

        checkerboard_pattern = Image.new("1", (width, width))
        ss = 1
        while ss <= (width / 2):
            for x in range(ss - 1, 2 * ss - 1):
                for y in range(0, width):
                    if (math.floor(y / ss) % 2) == 0:
                        checkerboard_pattern.putpixel((x, y), 1)
            ss *= 2

        five_horizontal_lines_top_and_bottom = Image.new("1", (40, width))
        # top
        for y0 in range(0, 10, 2):
            for x in range(40):
                y = y0 if x < 20 else y0 + 1
                five_horizontal_lines_top_and_bottom.putpixel((x, y), 1)
        # bottom
        for y0 in range(width - 10, width, 2):
            for x in range(40):
                y = y0 + 1 if x < 20 else y0
                five_horizontal_lines_top_and_bottom.putpixel((x, y), 1)

        bitmaps = [
            five_vertical_lines,
            checkerboard_pattern,
            five_horizontal_lines_top_and_bottom,
        ]
        render_engines = [_ImageRenderEngine(bitmap) for bitmap in bitmaps]
        super().__init__(render_engines=render_engines, padding=0)


class _ImageRenderEngine(RenderEngine):
    def __init__(self, image: Image.Image):
        super().__init__()
        self.image = image

    def render(self, _: RenderContext) -> Image.Image:
        return self.image
