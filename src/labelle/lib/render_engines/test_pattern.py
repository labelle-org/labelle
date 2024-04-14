import math

from PIL import Image

from labelle.lib.render_engines import RenderContext, RenderEngine


class TestPatternRenderEngine(RenderEngine):
    def __init__(self, width: int = 100):
        super().__init__()
        self.width = width

    def render(self, _: RenderContext) -> Image.Image:
        bitmap = Image.new("1", (10 + self.width + 2 + 40, self.width))

        # 5 vertical lines
        for x in range(0, 9, 2):
            for y in range(bitmap.height):
                bitmap.putpixel((x, y), 1)

        # checkerboard pattern
        cb = Image.new("1", (self.width, self.width))
        ss = 1
        while ss <= (self.width / 2):
            for x in range(ss - 1, 2 * ss - 1):
                for y in range(0, self.width):
                    if (math.floor(y / ss) % 2) == 0:
                        cb.putpixel((x, y), 1)
            ss *= 2
        bitmap.paste(cb, (10, 0))

        # a bunch of horizontal lines, on top and bottom
        hl = Image.new("1", (20, 9))
        for y in range(0, 9, 2):
            for x in range(20):
                hl.putpixel((x, y), 1)
        bitmap.paste(hl, (10 + self.width + 2, 0))
        bitmap.paste(hl, (10 + self.width + 2, self.width - 9))
        bitmap.paste(hl, (10 + self.width + 2 + 20, 1))
        bitmap.paste(hl, (10 + self.width + 2 + 20, self.width - 9 - 1))

        return bitmap
