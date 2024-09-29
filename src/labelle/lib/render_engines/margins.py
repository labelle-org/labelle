from __future__ import annotations

from typing import Literal, NamedTuple

from PIL import Image

from labelle.lib.constants import Direction
from labelle.lib.env_config import is_dev_mode_no_margins
from labelle.lib.render_engines.render_context import RenderContext
from labelle.lib.render_engines.render_engine import (
    RenderEngine,
    RenderEngineException,
)


class LabelMarginsPx(NamedTuple):
    horizontal: int
    vertical: int

class BitmapTooBigError(RenderEngineException):
    def __init__(self, width_px, max_width_px):
        msg = f"width_px: {width_px}, max_width_px: {max_width_px}"
        super().__init__(msg)


class MarginsRenderEngine(RenderEngine):
    label_margins_px: LabelMarginsPx
    min_width_px: int
    max_width_px: int
    visible_horizontal_margin_px: int
    render_engine: RenderEngine

    def __init__(
        self,
        render_engine: RenderEngine,
        mode: Literal["print", "preview"],
        justify: Direction = Direction.CENTER,
        visible_horizontal_margin_px: int = 0,
        labeler_margin_px: LabelMarginsPx | None = None,
        max_width_px: int | None = None,
        min_width_px: int | None = None,
    ):
        super().__init__()
        if labeler_margin_px is None:
            labeler_margin_px = LabelMarginsPx(horizontal=0, vertical=0)
        assert visible_horizontal_margin_px >= 0
        assert labeler_margin_px.horizontal >= 0
        assert labeler_margin_px.vertical >= 0
        assert not max_width_px or max_width_px >= 0
        if min_width_px is None:
            min_width_px = 0
        assert min_width_px >= 0
        self.mode = mode
        self.justify = justify
        if is_dev_mode_no_margins():
            self.visible_horizontal_margin_px = 0
            labeler_horizontal_margin_px = 0
            self.min_width_px = 0
        else:
            self.visible_horizontal_margin_px = visible_horizontal_margin_px
            labeler_horizontal_margin_px = labeler_margin_px.horizontal
            self.min_width_px = min_width_px
        labeler_vertical_margin_px = labeler_margin_px.vertical
        self.label_margins_px = LabelMarginsPx(
            horizontal=labeler_horizontal_margin_px,
            vertical=labeler_vertical_margin_px,
        )
        self.max_width_px = max_width_px
        self.render_engine = render_engine

    def _calculate_visible_width(self, payload_width_px: int) -> int:
        minimal_label_width_px = (
            payload_width_px + self.visible_horizontal_margin_px * 2
        )
        if self.max_width_px is not None and minimal_label_width_px > self.max_width_px:
            raise BitmapTooBigError(minimal_label_width_px, self.max_width_px)

        if self.min_width_px > minimal_label_width_px:
            label_width_px = self.min_width_px
        else:
            label_width_px = minimal_label_width_px
        return label_width_px

    def render(self, _: RenderContext) -> Image.Image:
        raise RuntimeError("This should never be called")

    def render_with_meta(
        self, context: RenderContext
    ) -> tuple[Image.Image, dict[str, int]]:
        payload_bitmap = self.render_engine.render(context)
        payload_width_px = payload_bitmap.width
        label_width_px = self._calculate_visible_width(payload_width_px)
        padding_px = label_width_px - payload_width_px  # sum of margins from both sides

        if self.justify == Direction.LEFT:
            horizontal_offset_px = self.visible_horizontal_margin_px
        elif self.justify == Direction.CENTER:
            horizontal_offset_px = padding_px // 2
        elif self.justify == Direction.RIGHT:
            horizontal_offset_px = padding_px - self.visible_horizontal_margin_px
        else:
            raise ValueError(f"Invalid justify value: {self.justify}")
        assert horizontal_offset_px >= self.visible_horizontal_margin_px

        # In print mode:
        # ==============
        # There is a gap between the printer head and the cutter (for the sake of this
        # example, let us say it is DX pixels wide).
        # We assume the printing starts when the print head is in offset DX from the
        # label's edge (the label's edge begins just under the cutter).
        # After we print the payload, we need to offset the label DX pixels, in order
        # to move the edge of the printed payload past the cutter, otherwise the cutter
        # will cut inside the printed payload.
        # Subsequently, in order to achieve symmetry so that the final margin matches
        # the initial margin, we add another offset of DX pixels, so that the cut will
        # have that same margin from both sides of the payload edge. In summary, due to
        # the gap between the printer head and the cutter of DX pixels, printing an
        # initial margin of 0 pixels and a final margin of 2 * DX pixels leaves an
        # effective margin of DX pixels on both sides.
        #
        # There's also some vertical margin between printed area and the label
        # edge

        if self.mode == "print":
            # print head is already in offset from label's edge under the cutter
            horizontal_offset_px -= self.label_margins_px.horizontal

        # add vertical margins to bitmap
        bitmap_height = (
            payload_bitmap.height + self.label_margins_px.vertical * 2
        )

        bitmap = Image.new("1", (label_width_px, bitmap_height))
        bitmap.paste(
            payload_bitmap,
            box=(horizontal_offset_px, self.label_margins_px.vertical),
        )
        meta = {
            "horizontal_offset_px": horizontal_offset_px,
            "vertical_offset_px": self.label_margins_px.vertical,
        }
        return bitmap, meta
