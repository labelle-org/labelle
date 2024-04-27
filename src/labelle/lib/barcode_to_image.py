# === LICENSE STATEMENT ===
# Copyright (c) 2011 Sebastian J. Bronner <waschtl@sbronner.com>
#
# Copying and distribution of this file, with or without modification, are
# permitted in any medium without royalty provided the copyright notice and
# this notice are preserved.
# === END LICENSE STATEMENT ===

from typing import List, Tuple, Union

from PIL import Image, ImageDraw

from labelle.lib.barcode_writer import BinaryString


def _mm2px(mm: float, dpi: float = 25.4) -> float:
    return (mm * dpi) / 25.4


def _list_of_runs(line: BinaryString) -> List[int]:
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
    quiet_zone: float,
    module_width: float,
    module_height: float,
    vertical_margin: float,
    dpi: float = 25.4,
) -> Tuple[int, int]:
    width = 2 * quiet_zone + modules_per_line * module_width
    height = vertical_margin * 2 + module_height
    return int(_mm2px(width, dpi)), int(_mm2px(height, dpi))


def convert_binary_string_to_barcode_image(
    line: BinaryString, quiet_zone: float, module_height: float
) -> Image.Image:
    """Render a barcode string into an image.

    line: A string of 0s and 1s representing the barcode.
    """
    module_width = 2
    vertical_margin = 8
    dpi = 25.4

    width, height = _calculate_size(
        modules_per_line=len(line),
        dpi=dpi,
        quiet_zone=quiet_zone,
        module_width=module_width,
        module_height=module_height,
        vertical_margin=vertical_margin,
    )
    image = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(image)

    ypos = vertical_margin
    mlist = _list_of_runs(line)
    # Left quiet zone is x startposition
    xpos = quiet_zone
    for mod in mlist:
        if mod < 1:
            color = 0
        else:
            color = 1
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
    return image


def _paint_module(
    *,
    xpos: float,
    ypos: float,
    width: float,
    color: Union[int, str],
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
