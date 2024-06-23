from __future__ import annotations

from typing import Sequence

from PIL import Image

from labelle.lib.render_engines.empty import EmptyRenderEngine
from labelle.lib.render_engines.render_context import RenderContext
from labelle.lib.render_engines.render_engine import RenderEngine


class HorizontallyCombinedRenderEngine(RenderEngine):
    padding: int

    def __init__(
        self,
        render_engines: Sequence[RenderEngine],
        padding: int = 4,
    ):
        super().__init__()
        self.render_engines = render_engines
        self.padding = padding

    def render(self, context: RenderContext) -> Image.Image:
        render_engines = self.render_engines or [EmptyRenderEngine()]
        bitmaps = [engine.render(context) for engine in render_engines]

        if len(bitmaps) == 1:
            merged_bitmap = bitmaps[0]
        else:
            label_height = max(b.height for b in bitmaps)
            total_width = _compute_total_width(bitmaps, self.padding)
            merged_bitmap = Image.new("1", (total_width, label_height))
            x_offset = 0
            for bitmap in bitmaps:
                y_offset = (label_height - bitmap.height) // 2
                merged_bitmap.paste(bitmap, box=(x_offset, y_offset))
                x_offset += bitmap.width + self.padding

        return merged_bitmap


def _compute_total_width(bitmaps: Sequence[Image.Image], padding: int) -> int:
    number_of_bitmaps = len(bitmaps)
    width_of_bitmaps = sum(b.width for b in bitmaps)

    # We alternate bitmaps and padding, and have bitmaps on each end.
    number_of_paddings = number_of_bitmaps - 1
    width_of_paddings = number_of_paddings * padding

    total_width = width_of_bitmaps + width_of_paddings
    return total_width
