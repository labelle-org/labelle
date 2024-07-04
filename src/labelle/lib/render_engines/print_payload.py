from __future__ import annotations

from PIL import Image

from labelle.lib.constants import Direction
from labelle.lib.render_engines.margins import LabelMarginsPx, MarginsRenderEngine
from labelle.lib.render_engines.render_context import RenderContext
from labelle.lib.render_engines.render_engine import RenderEngine


class PrintPayloadRenderEngine(RenderEngine):
    def __init__(
        self,
        render_engine: RenderEngine,
        justify: Direction = Direction.CENTER,
        visible_horizontal_margin_px: int = 0,
        labeler_margin_px: LabelMarginsPx | None = None,
        max_width_px: int | None = None,
        min_width_px: int | None = 0,
    ):
        super().__init__()
        self.render_engine = MarginsRenderEngine(
            render_engine=render_engine,
            mode="print",
            justify=justify,
            visible_horizontal_margin_px=visible_horizontal_margin_px,
            labeler_margin_px=labeler_margin_px,
            max_width_px=max_width_px,
            min_width_px=min_width_px,
        )

    def render(self, _: RenderContext) -> Image.Image:
        raise RuntimeError("This should never be called")

    def render_with_meta(
        self, context: RenderContext
    ) -> tuple[Image.Image, dict[str, int]]:
        return self.render_engine.render_with_meta(context)
