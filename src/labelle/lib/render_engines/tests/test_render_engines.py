from pathlib import Path

import PIL.ImageOps
import pytest

from labelle.lib.constants import Direction
from labelle.lib.render_engines import (
    BarcodeWithTextRenderEngine,
    RenderContext,
    TextRenderEngine,
)

RENDER_CONTEXT = RenderContext(height_px=100)
TESTS_DIR = Path(__file__).parent
FONT_FILE_NAME = "src/labelle/resources/fonts/Carlito-Regular.ttf"
EXPECTED_RENDERS_DIR = TESTS_DIR.joinpath("expected_renders")
OUTPUT_RENDER = TESTS_DIR.joinpath("output.png")
FONT_SIZE_RATIOS = [x / 10 for x in range(2, 11, 2)]


def verify_image(request, image_diff, image):
    filename = Path(request.node.name.replace(".", "_")).with_suffix(".png")
    actual = TESTS_DIR.joinpath(filename)
    inverted = PIL.ImageOps.invert(image.convert("RGB"))
    inverted.save(actual)
    expected = EXPECTED_RENDERS_DIR.joinpath(filename)
    image_diff(expected, actual, threshold=0.15)
    actual.unlink()


###############################
# BarcodeWithTextRenderEngine #
###############################


def test_barcode_with_text_render_engine(request, image_diff):
    render_engine = BarcodeWithTextRenderEngine(
        content="hello, world!",
        font_file_name=FONT_FILE_NAME,
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


@pytest.mark.parametrize("align", Direction)
def test_barcode_with_text_render_engine_alignment(request, image_diff, align):
    render_engine = BarcodeWithTextRenderEngine(
        content="hello, world!",
        font_file_name=FONT_FILE_NAME,
        align=align,
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


@pytest.mark.parametrize("font_size_ratio", [x / 10 for x in range(2, 11, 2)])
def test_barcode_with_text_render_engine_(request, image_diff, font_size_ratio):
    render_engine = BarcodeWithTextRenderEngine(
        content="hello, world!",
        font_file_name=FONT_FILE_NAME,
        font_size_ratio=font_size_ratio,
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


####################
# TextRenderEngine #
####################


def test_text_render_engine_single_line(request, image_diff):
    render_engine = TextRenderEngine(
        text_lines=["Hello, World!"],
        font_file_name=FONT_FILE_NAME,
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


def test_text_render_engine_with_frame(request, image_diff):
    render_engine = TextRenderEngine(
        text_lines=["Hello, World!"], font_file_name=FONT_FILE_NAME, frame_width_px=5
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


def test_text_render_engine_with_multiple_lines(request, image_diff):
    render_engine = TextRenderEngine(
        text_lines=["Hello,", "World!"],
        font_file_name=FONT_FILE_NAME,
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


@pytest.mark.parametrize("align", Direction)
def test_text_render_engine_alignment(request, image_diff, align):
    render_engine = TextRenderEngine(
        text_lines=["Hi,", "World!"],
        font_file_name=FONT_FILE_NAME,
        align=align,
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


@pytest.mark.parametrize("font_size_ratio", FONT_SIZE_RATIOS)
def test_text_render_engine_font_size_ratio(request, image_diff, font_size_ratio):
    render_engine = TextRenderEngine(
        text_lines=["Hello, World!"],
        font_file_name=FONT_FILE_NAME,
        font_size_ratio=font_size_ratio,
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


def test_text_render_engine_empty_line(request, image_diff):
    render_engine = TextRenderEngine(
        text_lines=[],
        font_file_name=FONT_FILE_NAME,
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


def test_text_render_engine_empty_lines(request, image_diff):
    render_engine = TextRenderEngine(
        text_lines=[],
        font_file_name=FONT_FILE_NAME,
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)
