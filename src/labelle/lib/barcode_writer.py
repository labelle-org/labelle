# === LICENSE STATEMENT ===
# Copyright (c) 2011 Sebastian J. Bronner <waschtl@sbronner.com>
#
# Copying and distribution of this file, with or without modification, are
# permitted in any medium without royalty provided the copyright notice and
# this notice are preserved.
# === END LICENSE STATEMENT ===

from typing import Optional

from barcode.writer import BaseWriter
from PIL import Image, ImageDraw


def mm2px(mm, dpi=25.4):
    return (mm * dpi) / 25.4


class BarcodeImageWriter(BaseWriter):
    _draw: Optional[ImageDraw.ImageDraw]

    def __init__(self):
        super().__init__(self._init, self._paint_module, None, self._finish)
        self.format = "PNG"
        self.dpi = 25.4
        self._image = None
        self._draw = None
        self.vertical_margin = 0

    def calculate_size(self, modules_per_line, number_of_lines, dpi=25.4):
        width = 2 * self.quiet_zone + modules_per_line * self.module_width
        height = self.vertical_margin * 2 + self.module_height * number_of_lines
        return int(mm2px(width, dpi)), int(mm2px(height, dpi))

    def render(self, code):
        """Render the barcode.

        Uses whichever inheriting writer is provided via the registered callbacks.

        :parameters:
            code : List
                List of strings matching the writer spec
                (only contain 0 or 1).
        """
        if self._callbacks["initialize"] is not None:
            self._callbacks["initialize"](code)
        ypos = self.vertical_margin
        for cc, line in enumerate(code):
            # Pack line to list give better gfx result, otherwise in can
            # result in aliasing gaps
            # '11010111' -> [2, -1, 1, -1, 3]
            line += " "
            c = 1
            mlist = []
            for i in range(0, len(line) - 1):
                if line[i] == line[i + 1]:
                    c += 1
                else:
                    if line[i] == "1":
                        mlist.append(c)
                    else:
                        mlist.append(-c)
                    c = 1
            # Left quiet zone is x startposition
            xpos = self.quiet_zone
            for mod in mlist:
                if mod < 1:
                    color = self.background
                else:
                    color = self.foreground
                # remove painting for background colored tiles?
                self._callbacks["paint_module"](
                    xpos, ypos, self.module_width * abs(mod), color
                )
                xpos += self.module_width * abs(mod)
            # Add right quiet zone to every line, except last line,
            # quiet zone already provided with background,
            # should it be removed complety?
            if (cc + 1) != len(code):
                self._callbacks["paint_module"](
                    xpos, ypos, self.quiet_zone, self.background
                )
            ypos += self.module_height
        return self._callbacks["finish"]()

    def _init(self, code):
        size = self.calculate_size(len(code[0]), len(code), self.dpi)
        self._image = Image.new("1", size, self.background)
        self._draw = ImageDraw.Draw(self._image)

    def _paint_module(self, xpos, ypos, width, color):
        size = (
            (mm2px(xpos, self.dpi), mm2px(ypos, self.dpi)),
            (
                mm2px(xpos + width, self.dpi),
                mm2px(ypos + self.module_height, self.dpi),
            ),
        )
        assert self._draw is not None
        self._draw.rectangle(size, outline=color, fill=color)

    def _finish(self):
        # although Image mode set to "1", draw function writes white as 255
        assert self._image is not None
        self._image = self._image.point(lambda x: 1 if x > 0 else 0, mode="1")
        return self._image

    def save(self, filename, output):
        filename = f"{filename}.{self.format.lower()}"
        output.save(filename, self.format.upper())
        return filename
