import webbrowser
from tempfile import NamedTemporaryFile

import typer
from PIL import Image, ImageOps

from labelle.lib.constants import Output
from labelle.lib.unicode_blocks import image_to_unicode


def output_bitmap(bitmap: Image.Image, output: Output):
    if output in (Output.CONSOLE, Output.CONSOLE_INVERTED):
        label_rotated = bitmap.transpose(Image.Transpose.ROTATE_270)
        invert = output == Output.CONSOLE_INVERTED
        typer.echo(image_to_unicode(label_rotated, invert=invert))
    if output == Output.IMAGEMAGICK:
        ImageOps.invert(bitmap.convert("RGB")).show()
    if output == Output.BROWSER:
        with NamedTemporaryFile(suffix=".png", delete=False) as fp:
            inverted = ImageOps.invert(bitmap.convert("RGB"))
            ImageOps.invert(inverted).save(fp)
            webbrowser.open(f"file://{fp.name}")
