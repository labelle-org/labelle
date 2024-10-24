# === LICENSE STATEMENT ===
# Copyright (c) 2011 Sebastian J. Bronner <waschtl@sbronner.com>
#
# Copying and distribution of this file, with or without modification, are
# permitted in any medium without royalty provided the copyright notice and
# this notice are preserved.
# === END LICENSE STATEMENT ===
import contextlib
import logging
import sys
from typing import Generator, List, Tuple

from PIL import ImageDraw

from labelle.lib.logger import print_exception

LOG = logging.getLogger(__name__)


def scaling(pix, sc) -> List[Tuple[int, int]]:
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


@contextlib.contextmanager
def system_run() -> Generator[None, None, None]:
    try:
        yield
    except Exception as e:  # noqa: BLE001
        print_exception(e)
        sys.exit(1)
