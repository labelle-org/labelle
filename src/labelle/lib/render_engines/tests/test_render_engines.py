from pathlib import Path

import PIL.ImageOps
import pytest

from labelle.lib.constants import DEFAULT_BARCODE_TYPE, BarcodeType, Direction
from labelle.lib.render_engines import (
    BarcodeRenderEngine,
    BarcodeRenderError,
    BarcodeWithTextRenderEngine,
    EmptyRenderEngine,
    HorizontallyCombinedRenderEngine,
    NoContentError,
    PicturePathDoesNotExist,
    PictureRenderEngine,
    QrRenderEngine,
    QrTooBigError,
    RenderContext,
    SamplePatternRenderEngine,
    TextRenderEngine,
    UnidentifiedImageFileError,
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
    # Note: threshold should be omitted in the future
    # (CI bitmaps are different than development machine)
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
def test_barcode_with_text_render_engine_font_size_ratio(
    request, image_diff, font_size_ratio
):
    render_engine = BarcodeWithTextRenderEngine(
        content="hello, world!",
        font_file_name=FONT_FILE_NAME,
        font_size_ratio=font_size_ratio,
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


#######################
# BarcodeRenderEngine #
#######################


def test_barcode_render_engine(request, image_diff):
    render_engine = BarcodeRenderEngine(
        content="hello, world!",
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


@pytest.mark.parametrize(
    "barcode_type,content",
    [
        (BarcodeType.EAN, "123456789012"),
        (BarcodeType.UPC, "12345678901"),
        (BarcodeType.CODE39, "123"),
        (DEFAULT_BARCODE_TYPE, " "),
        # Empty string in default type should be replaced with a space
        (DEFAULT_BARCODE_TYPE, ""),
    ],
)
def test_barcode_render_engine_barcode_type(request, image_diff, barcode_type, content):
    render_engine = BarcodeRenderEngine(content=content, barcode_type=barcode_type)
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


def test_barcode_render_engine_default_barcode_type():
    """Test default type handling.

    Test our mechanism of replacing an empty string with a space for the default
    barcode type, to prevent an error.
    """
    images = [
        BarcodeRenderEngine(content=content, barcode_type=DEFAULT_BARCODE_TYPE).render(
            RENDER_CONTEXT
        )
        for content in ["", " "]
    ]
    assert images[0].tobytes() == images[1].tobytes()


def test_barcode_render_engine_internal_error():
    render_engine = BarcodeRenderEngine(
        content="No alphabet allowed", barcode_type=BarcodeType.EAN
    )
    with pytest.raises(BarcodeRenderError) as exc_info:
        render_engine.render(RENDER_CONTEXT)
    assert (
        str(exc_info.value) == "Barcode render error: IllegalCharacterError("
        "'EAN code can only contain numbers.')"
    )


#####################
# EmptyRenderEngine #
#####################


@pytest.mark.parametrize("width_px", [1, 10, 100])
def test_empty_render_engine(request, image_diff, width_px):
    render_engine = EmptyRenderEngine(
        width_px=width_px,
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


####################################
# HorizontallyCombinedRenderEngine #
####################################


def test_horizontally_combined_render_engine_single(request, image_diff):
    inner_render_engine = TextRenderEngine(
        text_lines=["Hello, World!"],
        font_file_name=FONT_FILE_NAME,
    )
    render_engine = HorizontallyCombinedRenderEngine(
        render_engines=[inner_render_engine]
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


def test_horizontally_combined_render_engine_multiple(request, image_diff):
    inner_render_engines = [
        TextRenderEngine(
            text_lines=[f"Render #{i}"],
            font_file_name=FONT_FILE_NAME,
        )
        for i in range(1, 4)
    ]
    render_engine = HorizontallyCombinedRenderEngine(
        render_engines=inner_render_engines
    )
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


def test_horizontally_combined_render_engine_empty(request, image_diff):
    render_engine = HorizontallyCombinedRenderEngine(render_engines=[])
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


#######################
# PictureRenderEngine #
#######################


def test_picture_render_engine(request, image_diff):
    render_engine = PictureRenderEngine(picture_path="labelle.png")
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


def test_picture_render_engine_bad_path():
    with pytest.raises(PicturePathDoesNotExist) as exc_info:
        PictureRenderEngine(picture_path="non_existent.png")
    assert str(exc_info.value) == "Picture path does not exist: non_existent.png"


def test_picture_render_engine_empty_path():
    with pytest.raises(NoContentError):
        PictureRenderEngine(picture_path="")


def test_picture_render_engine_bad_image_file():
    render_engine = PictureRenderEngine(picture_path="README.md")
    with pytest.raises(UnidentifiedImageFileError) as exc_info:
        render_engine.render(RENDER_CONTEXT)
    assert str(exc_info.value).startswith("cannot identify image file")


##################
# QrRenderEngine #
##################


def test_qr_render_engine(request, image_diff):
    render_engine = QrRenderEngine(content="Hello, World!")
    image = render_engine.render(RENDER_CONTEXT)
    verify_image(request, image_diff, image)


def test_qr_render_engine_no_content():
    with pytest.raises(NoContentError):
        QrRenderEngine(content="")


def test_qr_render_engine_too_big():
    render_engine = QrRenderEngine(content="Hello, World!" * 100)
    with pytest.raises(QrTooBigError) as exc_info:
        render_engine.render(RENDER_CONTEXT)
    assert str(exc_info.value) == "Too much information to store in the QR code"


#############################
# SamplePatternRenderEngine #
#############################


@pytest.mark.parametrize("height", [15, 64, 65, 100, 256])
def test_sample_pattern_render_engine(request, image_diff, height):
    render_engine = SamplePatternRenderEngine(height=height)
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
