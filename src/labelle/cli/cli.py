# === LICENSE STATEMENT ===
# Copyright (c) 2011 Sebastian J. Bronner <waschtl@sbronner.com>
#
# Copying and distribution of this file, with or without modification, are
# permitted in any medium without royalty provided the copyright notice and
# this notice are preserved.
# === END LICENSE STATEMENT ===
import logging
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from labelle import __version__
from labelle.lib.constants import (
    DEFAULT_BARCODE_TYPE,
    DEFAULT_MARGIN_PX,
    PIXELS_PER_MM,
    USE_QR,
    BarcodeType,
    Direction,
    Output,
    e_qrcode,
)
from labelle.lib.devices.device_manager import DeviceManager, DeviceManagerNoDevices
from labelle.lib.devices.dymo_labeler import DymoLabeler
from labelle.lib.env_config import is_verbose_env_vars
from labelle.lib.font_config import (
    DefaultFontStyle,
    FontStyle,
    NoFontFound,
    get_available_fonts,
    get_font_path,
)
from labelle.lib.logger import configure_logging, set_not_verbose
from labelle.lib.outputs import output_bitmap
from labelle.lib.render_engines import (
    BarcodeRenderEngine,
    BarcodeWithTextRenderEngine,
    HorizontallyCombinedRenderEngine,
    PictureRenderEngine,
    PrintPayloadRenderEngine,
    PrintPreviewRenderEngine,
    QrRenderEngine,
    RenderContext,
    RenderEngine,
    TestPatternRenderEngine,
    TextRenderEngine,
)

LOG = logging.getLogger(__name__)


def mm_to_payload_px(mm: float, margin: float):
    """Convert a length in mm to a number of pixels of payload.

    The print resolution is 7 pixels/mm, and margin is subtracted from each side.
    """
    return max(0, (mm * PIXELS_PER_MM) - margin * 2)


def version_callback(value: bool):
    if value:
        typer.echo(f"Labelle: {__version__}")
        raise typer.Exit()


def qr_callback(qr_content: str) -> str:
    # check if barcode, qrcode or text should be printed, use frames only on text
    if qr_content and not USE_QR:
        raise typer.BadParameter(
            "QR code cannot be used without QR support installed"
        ) from e_qrcode
    return qr_content


def get_device_manager() -> DeviceManager:
    device_manager = DeviceManager()
    try:
        device_manager.scan()
    except DeviceManagerNoDevices as e:
        err_console = Console(stderr=True)
        err_console.print(f"Error: {e}")
        raise typer.Exit() from e
    return device_manager


app = typer.Typer()


@app.command(hidden=True)
def list_devices():
    device_manager = get_device_manager()
    console = Console()
    headers = ["Manufacturer", "Product", "Serial Number", "USB"]
    table = Table(*headers, show_header=True)
    for device in device_manager.devices:
        table.add_row(
            device.manufacturer, device.product, device.serial_number, device.usb_id
        )
    console.print(table)
    raise typer.Exit()


@app.callback(invoke_without_command=True)
def default(
    ctx: typer.Context,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show application version",
        ),
    ] = None,
    device_pattern: Annotated[
        Optional[List[str]],
        typer.Option(
            "--device",
            help=(
                "Select a particular device by filtering for a given substring "
                "in the device's manufacturer, product or serial number"
            ),
            rich_help_panel="Device Configuration",
        ),
    ] = None,
    text: Annotated[
        Optional[List[str]],
        typer.Argument(
            help="Text, each parameter gives a new line",
            rich_help_panel="Elements",
        ),
    ] = None,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Increase logging verbosity")
    ] = False,
    style: Annotated[
        FontStyle, typer.Option(help="Set fonts style", rich_help_panel="Design")
    ] = DefaultFontStyle,
    frame_width_px: Annotated[
        Optional[int],
        typer.Option(
            help="Draw frame around the text, more arguments for thicker frame",
            rich_help_panel="Design",
        ),
    ] = None,
    align: Annotated[
        Direction, typer.Option(help="Align multiline text", rich_help_panel="Design")
    ] = Direction.LEFT,
    justify: Annotated[
        Direction,
        typer.Option(
            help="Justify content of label if label content is less than the minimum or"
            " fixed length",
            rich_help_panel="Design",
        ),
    ] = Direction.LEFT,
    test_pattern: Annotated[
        Optional[int],
        typer.Option(help="Prints test pattern of a desired dot width"),
    ] = None,
    min_length: Annotated[
        Optional[float],
        typer.Option(
            help="Minimum label length [mm]", rich_help_panel="Label Dimensions"
        ),
    ] = None,
    max_length: Annotated[
        Optional[float],
        typer.Option(
            help="Maximum label length [mm], error if the label won't fit",
            rich_help_panel="Label Dimensions",
        ),
    ] = None,
    fixed_length: Annotated[
        Optional[float],
        typer.Option(
            help="Fixed label length [mm], error if the label won't fit",
            rich_help_panel="Label Dimensions",
        ),
    ] = None,
    output: Annotated[
        Output,
        typer.Option(help="Destination of the label render"),
    ] = Output.PRINTER,
    font: Annotated[
        Optional[str],
        typer.Option(
            help="User font. Overrides --style parameter", rich_help_panel="Design"
        ),
    ] = None,
    qr_content: Annotated[
        Optional[str],
        typer.Option(
            "--qr", callback=qr_callback, help="QR code", rich_help_panel="Elements"
        ),
    ] = None,
    barcode_content: Annotated[
        Optional[str],
        typer.Option("--barcode", help="Barcode", rich_help_panel="Elements"),
    ] = None,
    barcode_type: Annotated[
        Optional[BarcodeType],
        typer.Option(
            help="Barcode type",
            show_default=DEFAULT_BARCODE_TYPE.value,
            rich_help_panel="Elements",
        ),
    ] = None,
    barcode_with_text_content: Annotated[
        Optional[str],
        typer.Option(
            "--barcode-with-text", help="Barcode with text", rich_help_panel="Elements"
        ),
    ] = None,
    picture: Annotated[
        Optional[Path], typer.Option(help="Picture", rich_help_panel="Elements")
    ] = None,
    margin_px: Annotated[
        float,
        typer.Option(
            help="Horizontal margins [px]", rich_help_panel="Label Dimensions"
        ),
    ] = DEFAULT_MARGIN_PX,
    font_scale: Annotated[
        float,
        typer.Option(help="Scaling font factor, [0,100] [%]", rich_help_panel="Design"),
    ] = 90,
    tape_size_mm: Annotated[
        Optional[int],
        typer.Option(help="Tape size [mm]", rich_help_panel="Device Configuration"),
    ] = None,
):
    if ctx.invoked_subcommand is not None:
        return

    if (not verbose) and (not is_verbose_env_vars()):
        # Neither --verbose flag nor the environment variable is set.
        set_not_verbose()

    # read config file
    try:
        font_path = get_font_path(font=font, style=style)
    except NoFontFound as e:
        valid_font_names = [f.stem for f in get_available_fonts()]
        msg = f"{e}. Valid fonts are: {', '.join(valid_font_names)}"
        raise typer.BadParameter(msg) from None

    if barcode_type and not (barcode_content or barcode_with_text_content):
        raise typer.BadParameter("Cannot specify barcode type without a barcode value")

    if barcode_with_text_content and barcode_content:
        raise typer.BadParameter(
            "Cannot specify both barcode with text and regular barcode"
        )

    if fixed_length is not None and (min_length != 0 or max_length is not None):
        raise typer.BadParameter(
            "Cannot specify min/max and fixed length at the same time"
        )

    if min_length is None:
        min_length = 0.0
    if min_length < 0:
        raise typer.BadParameter("Minimum length must be non-negative number")
    if max_length is not None:
        if max_length <= 0:
            raise typer.BadParameter("Maximum length must be positive number")
        if max_length < min_length:
            raise typer.BadParameter("Maximum length is less than minimum length")

    render_engines: list[RenderEngine] = []

    if test_pattern:
        render_engines.append(TestPatternRenderEngine(test_pattern))

    if qr_content:
        render_engines.append(QrRenderEngine(qr_content))

    if barcode_with_text_content:
        render_engines.append(
            BarcodeWithTextRenderEngine(
                content=barcode_with_text_content,
                barcode_type=barcode_type,
                font_file_name=font_path,
                frame_width_px=frame_width_px,
            )
        )

    if barcode_content:
        render_engines.append(
            BarcodeRenderEngine(content=barcode_content, barcode_type=barcode_type)
        )

    if text:
        render_engines.append(
            TextRenderEngine(
                text_lines=text,
                font_file_name=font_path,
                frame_width_px=frame_width_px,
                font_size_ratio=int(font_scale) / 100.0,
                align=align,
            )
        )

    if picture:
        render_engines.append(PictureRenderEngine(picture))

    if fixed_length is None:
        min_label_mm_len = min_length
        max_label_mm_len = max_length
    else:
        min_label_mm_len = fixed_length
        max_label_mm_len = fixed_length

    min_payload_len_px = mm_to_payload_px(min_label_mm_len, margin_px)
    max_payload_len_px = (
        mm_to_payload_px(max_label_mm_len, margin_px)
        if max_label_mm_len is not None
        else None
    )

    if output == Output.PRINTER:
        device_manager = get_device_manager()
        device = device_manager.find_and_select_device(patterns=device_pattern)
        device.setup()
    else:
        device = None

    dymo_labeler = DymoLabeler(tape_size_mm=tape_size_mm, device=device)
    render_engine = HorizontallyCombinedRenderEngine(render_engines)
    render_context = RenderContext(
        background_color="white",
        foreground_color="black",
        height_px=dymo_labeler.height_px,
        preview_show_margins=False,
    )

    # print or show the label
    render: RenderEngine
    if output == Output.PRINTER:
        render = PrintPayloadRenderEngine(
            render_engine=render_engine,
            justify=justify,
            visible_horizontal_margin_px=margin_px,
            labeler_margin_px=dymo_labeler.labeler_margin_px,
            max_width_px=max_payload_len_px,
            min_width_px=min_payload_len_px,
        )
        bitmap, _ = render.render_with_meta(render_context)
        dymo_labeler.print(bitmap)
    else:
        render = PrintPreviewRenderEngine(
            render_engine=render_engine,
            justify=justify,
            visible_horizontal_margin_px=margin_px,
            labeler_margin_px=dymo_labeler.labeler_margin_px,
            max_width_px=max_payload_len_px,
            min_width_px=min_payload_len_px,
        )
        bitmap = render.render(render_context)
        output_bitmap(bitmap, output)


def main():
    configure_logging()
    app()


if __name__ == "__main__":
    main()
