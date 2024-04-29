from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageOps

from labelle.lib.render_engines.render_context import RenderContext
from labelle.lib.render_engines.render_engine import (
    RenderEngine,
    RenderEngineException,
)


class PicturePathDoesNotExist(RenderEngineException):
    pass


class PictureRenderEngine(RenderEngine):
    def __init__(self, picture_path: Path | str) -> None:
        super().__init__()
        self.picture_path = Path(picture_path)
        if not self.picture_path.is_file():
            raise PicturePathDoesNotExist(
                f"Picture path does not exist: {picture_path}"
            )

    def render(self, context: RenderContext) -> Image.Image:
        height_px = context.height_px
        with Image.open(self.picture_path) as img:
            if img.height > height_px:
                ratio = height_px / img.height
                img = img.resize((int(math.ceil(img.width * ratio)), height_px))

            img = img.convert("L", palette=Image.AFFINE)
            return ImageOps.invert(img).convert("1")
