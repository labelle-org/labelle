# === LICENSE STATEMENT ===
# Copyright (c) 2011 Sebastian J. Bronner <waschtl@sbronner.com>
#
# Copying and distribution of this file, with or without modification, are
# permitted in any medium without royalty provided the copyright notice and
# this notice are preserved.
# === END LICENSE STATEMENT ===

from typing import List, Tuple

from barcode.writer import BaseWriter
from PIL import Image, ImageDraw


def _mm2px(mm: float, dpi: float = 25.4) -> float:
    return (mm * dpi) / 25.4


def _list_of_runs(line: str) -> List[int]:
    # Pack line to list give better gfx result, otherwise in can
    # result in aliasing gaps
    # '11010111' -> [2, -1, 1, -1, 3]
    c = 1
    mlist = []
    for i in range(0, len(line)):
        if i + 1 < len(line) and line[i] == line[i + 1]:
            c += 1
        else:
            if line[i] == "1":
                mlist.append(c)
            else:
                mlist.append(-c)
            c = 1
    return mlist


def _calculate_size(
    *,
    modules_per_line: int,
    number_of_lines: int,
    quiet_zone: float,
    module_width: float,
    module_height: float,
    vertical_margin: float,
    dpi: float = 25.4,
) -> Tuple[int, int]:
    width = 2 * quiet_zone + modules_per_line * module_width
    height = vertical_margin * 2 + module_height * number_of_lines
    return int(_mm2px(width, dpi)), int(_mm2px(height, dpi))


class BarcodeImageWriter(BaseWriter):
    def render(self, code: List[str]) -> Image.Image:
        """Render the barcode.

        Uses whichever inheriting writer is provided via the registered callbacks.

        :parameters:
            code : List
                List of strings matching the writer spec
                (only contain 0 or 1).
        """
        quiet_zone = self.quiet_zone
        module_height = self.module_height

        module_width = 2
        background = "black"
        foreground = "white"
        vertical_margin = 8
        dpi = 25.4

        width, height = _calculate_size(
            modules_per_line=len(code[0]),
            number_of_lines=len(code),
            dpi=dpi,
            quiet_zone=quiet_zone,
            module_width=module_width,
            module_height=module_height,
            vertical_margin=vertical_margin,
        )
        image = Image.new("1", (width, height), background)
        draw = ImageDraw.Draw(image)

        ypos = vertical_margin
        if len(code) != 1:
            raise ValueError("Barcode expected to have only one line")
        line = code[0]
        mlist = _list_of_runs(line)
        # Left quiet zone is x startposition
        xpos = quiet_zone
        for mod in mlist:
            if mod < 1:
                color = background
            else:
                color = foreground
            # remove painting for background colored tiles?
            _paint_module(
                xpos=xpos,
                ypos=ypos,
                width=module_width * abs(mod),
                color=color,
                dpi=dpi,
                module_height=module_height,
                draw=draw,
            )
            xpos += module_width * abs(mod)
        return _finish(image)


def _paint_module(
    *,
    xpos: float,
    ypos: float,
    width: float,
    color: str,
    dpi: float,
    module_height: float,
    draw: ImageDraw.ImageDraw,
) -> None:
    size = (
        (_mm2px(xpos, dpi), _mm2px(ypos, dpi)),
        (
            _mm2px(xpos + width, dpi),
            _mm2px(ypos + module_height, dpi),
        ),
    )
    draw.rectangle(size, outline=color, fill=color)


def _finish(image: Image.Image) -> Image.Image:
    # although Image mode set to "1", draw function writes white as 255
    return image.point(lambda x: 1 if x > 0 else 0, mode="1")
