from PIL import Image

from labelle.lib.constants import QRCode
from labelle.lib.render_engines.render_context import RenderContext
from labelle.lib.render_engines.render_engine import (
    RenderEngine,
    RenderEngineException,
)
from labelle.lib.utils import draw_image, scaling


class QrTooBigError(RenderEngineException):
    def __init__(self):
        msg = "Too much information to store in the QR code"
        super().__init__(msg)


class NoContentError(RenderEngineException):
    pass


class QrRenderEngine(RenderEngine):
    _content: str

    def __init__(self, content):
        super().__init__()
        if not len(content):
            raise NoContentError()
        self._content = content

    def render(self, context: RenderContext) -> Image.Image:
        # create QR object from first string
        code = QRCode(self._content, error="M")
        qr_text_lines = code.text(quiet_zone=1).split()

        # create an empty label image
        height_px = context.height_px
        qr_scale = height_px // len(qr_text_lines)
        qr_offset = (height_px - len(qr_text_lines) * qr_scale) // 2
        label_width_px = len(qr_text_lines[0]) * qr_scale

        if not qr_scale:
            raise QrTooBigError()

        bitmap = Image.new("1", (label_width_px, height_px))

        with draw_image(bitmap) as draw:
            # write the qr-code into the empty image
            for i, line in enumerate(qr_text_lines):
                for j, char in enumerate(line):
                    if char == "1":
                        qr_pixels = scaling(
                            (j * qr_scale, i * qr_scale + qr_offset), qr_scale
                        )
                        draw.point(qr_pixels, 1)
        return bitmap
