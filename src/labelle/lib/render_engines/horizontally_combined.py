from __future__ import annotations

from typing import Sequence

from PIL import Image

from labelle.lib.render_engines.empty import EmptyRenderEngine
from labelle.lib.render_engines.render_context import RenderContext
from labelle.lib.render_engines.render_engine import RenderEngine


class HorizontallyCombinedRenderEngine(RenderEngine):
    PADDING = 4

    def __init__(
        self,
        render_engines: Sequence[RenderEngine],
    ):
        super().__init__()
        self.render_engines = render_engines

    def render(self, context: RenderContext) -> Image.Image:
        render_engines = self.render_engines or [EmptyRenderEngine()]
        bitmaps = [engine.render(context) for engine in render_engines]

        if len(bitmaps) == 1:
            merged_bitmap = bitmaps[0]
        else:
            label_height = max(b.height for b in bitmaps)
            merged_bitmap = Image.new(
                "1",
                (
                    sum(b.width for b in bitmaps) + self.PADDING * (len(bitmaps) - 1),
                    label_height,
                ),
            )
            x_offset = 0
            for bitmap in bitmaps:
                y_offset = (label_height - bitmap.size[1]) // 2
                merged_bitmap.paste(bitmap, box=(x_offset, y_offset))
                x_offset += bitmap.width + self.PADDING

        return merged_bitmap
