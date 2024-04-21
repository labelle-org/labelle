from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image

from labelle.lib.render_engines.render_context import RenderContext


class RenderEngineException(Exception):
    pass


class RenderEngine(ABC):
    @abstractmethod
    def render(self, context: RenderContext) -> Image.Image:
        raise NotImplementedError()

    def render_with_meta(
        self, context: RenderContext
    ) -> tuple[Image.Image, dict[str, float] | None]:
        return self.render(context), None
