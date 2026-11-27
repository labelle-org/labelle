# === LICENSE STATEMENT ===
# Copyright (c) 2011 Sebastian J. Bronner <waschtl@sbronner.com>
#
# Copying and distribution of this file, with or without modification, are
# permitted in any medium without royalty provided the copyright notice and
# this notice are preserved.
# === END LICENSE STATEMENT ===
import contextlib
import logging
import math
import sys
from collections.abc import Generator

from PIL import ImageDraw

from labelle.lib.constants import DPI, MM_PER_INCH
from labelle.lib.logger import print_exception

LOG = logging.getLogger(__name__)


def scaling(pix, sc) -> list[tuple[int, int]]:
    """Scaling pixel up, input: (x,y),scale-factor."""
    return [(pix[0] + i, pix[1] + j) for i in range(sc) for j in range(sc)]


@contextlib.contextmanager
def draw_image(bitmap) -> Generator[ImageDraw.ImageDraw, None, None]:
    drawobj = ImageDraw.Draw(bitmap)
    assert isinstance(drawobj, ImageDraw.ImageDraw)
    try:
        yield drawobj
    finally:
        del drawobj


def px_to_mm(px, dpi: float = DPI) -> float:
    mm = px * MM_PER_INCH / dpi
    # Round up to nearest 0.1mm
    return math.ceil(mm * 10) / 10


def mm_to_px(mm, dpi: float = DPI) -> float:
    return mm * dpi / MM_PER_INCH


@contextlib.contextmanager
def system_run() -> Generator[None, None, None]:
    try:
        yield
    except Exception as e:  # noqa: BLE001
        print_exception(e)
        sys.exit(1)
