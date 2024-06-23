# === LICENSE STATEMENT ===
# Copyright (c) 2011 Sebastian J. Bronner <waschtl@sbronner.com>
#
# Copying and distribution of this file, with or without modification, are
# permitted in any medium without royalty provided the copyright notice and
# this notice are preserved.
# === END LICENSE STATEMENT ===

# On systems with access to sysfs under /sys, this script will use the three
# variables DEV_CLASS, DEV_VENDOR, and DEV_PRODUCT to find the device file
# under /dev automatically. This behavior can be overridden by setting the
# variable DEV_NODE to the device file path. This is intended for cases, where
# either sysfs is unavailable or unusable by this script for some reason.
# Please beware that DEV_NODE must be set to None when not used, else you will
# be bitten by the NameError exception.
from enum import Enum
from pathlib import Path

import labelle.resources.fonts
import labelle.resources.icons
from labelle.lib.devices.device_config import DeviceConfig

try:
    from pyqrcode import QRCode

    USE_QR = True
    e_qrcode = None
except ImportError as error:  # pragma: no cover
    e_qrcode = error
    USE_QR = False
    QRCode = None


UNCONFIRMED_MESSAGE = (
    "WARNING: This device is not confirmed to work with this software. Please "
    "report your experiences in https://github.com/labelle-org/labelle/issues/4"
)

# ---- Supported USB Devices configuration ----
SUPPORTED_PRODUCTS = [
    DeviceConfig(
        name="DYMO LabelMANAGER PC",
        device_ids=[0x0011],
        # ToDo: Validate config!
        # Printhead 128 Pixels, distributed over 18mm of active area
        print_head_width_px=128,
        print_head_active_area_width_mm=18,
        supported_tape_sizes_mm=[6, 9, 12, 19],
    ),
    DeviceConfig(
        name="LabelPoint 350",
        device_ids=[0x0015],
        # ToDo: Validate config!
        # Printhead 64 Pixels, distributed over 9mm of active area
        print_head_width_px=64,
        print_head_active_area_width_mm=9,
        supported_tape_sizes_mm=[6, 9, 12],
    ),
    DeviceConfig(
        name="DYMO LabelMANAGER PC II",
        device_ids=[0x001C],
        # Printhead 128 Pixels, distributed over 18mm of active area
        print_head_width_px=128,
        print_head_active_area_width_mm=18,
        supported_tape_sizes_mm=[6, 9, 12, 19, 24],
    ),
    DeviceConfig(
        name="LabelManager PnP",
        device_ids=[0x1001, 0x1002],
        # Printhead 64 Pixels, distributed over 9mm of active area
        print_head_width_px=64,
        print_head_active_area_width_mm=9,
        supported_tape_sizes_mm=[6, 9, 12],
    ),
    DeviceConfig(
        name=f"LabelManager 420P {UNCONFIRMED_MESSAGE}",
        device_ids=[0x1003, 0x1004],
        # ToDo: Validate config!
        # Printhead 64 Pixels, distributed over 9mm of active area
        print_head_width_px=64,
        print_head_active_area_width_mm=9,
        supported_tape_sizes_mm=[6, 9, 12],
    ),
    DeviceConfig(
        name="LabelManager 280",
        device_ids=[0x1006, 0x1005],
        # ToDo: Validate config!
        # Printhead 64 Pixels, distributed over 9mm of active area
        print_head_width_px=64,
        print_head_active_area_width_mm=9,
        supported_tape_sizes_mm=[6, 9, 12],
    ),
    DeviceConfig(
        name=f"LabelManager Wireless PnP {UNCONFIRMED_MESSAGE}",
        device_ids=[0x1007, 0x1008],
        # ToDo: Validate config!
        # Printhead 64 Pixels, distributed over 9mm of active area
        print_head_width_px=64,
        print_head_active_area_width_mm=9,
        supported_tape_sizes_mm=[6, 9, 12],
    ),
    DeviceConfig(
        name=f"MobileLabeler {UNCONFIRMED_MESSAGE}",
        device_ids=[0x1009],
        # ToDo: Validate config!
        # Printhead 64 Pixels, distributed over 9mm of active area
        print_head_width_px=64,
        print_head_active_area_width_mm=9,
        supported_tape_sizes_mm=[6, 9, 12],
    ),
]

# Simulator configuration
SIMULATOR_CONFIG = DeviceConfig(
    name="Simulator",
    device_ids=[0],
    # Fake printhead 128 Pixels, distributed over 18mm of active area
    print_head_width_px=128,
    print_head_active_area_width_mm=18,
    supported_tape_sizes_mm=[6, 9, 12, 19, 24],
)


DEV_VENDOR = 0x0922

PRINTER_INTERFACE_CLASS = 0x07
HID_INTERFACE_CLASS = 0x03

# Escape character preceeding all commands
ESC = 0x1B

# Synchronization character preceding uncompressed print data
SYN = 0x16

FONT_SIZERATIO = 7 / 8

DEFAULT_MARGIN_PX = 56
VERTICAL_PREVIEW_MARGIN_PX = 13

DPI = 180
MM_PER_INCH = 25.4
PIXELS_PER_MM = DPI / MM_PER_INCH

ICON_DIR = Path(labelle.resources.icons.__file__).parent


class BarcodeType(str, Enum):
    CODE128 = "code128"
    CODE39 = "code39"
    CODABAR = "codabar"
    EAN = "ean"
    EAN13 = "ean13"
    EAN13_GUARD = "ean13-guard"
    EAN14 = "ean14"
    EAN8 = "ean8"
    EAN8_GUARD = "ean8-guard"
    GS1 = "gs1"
    GS1_128 = "gs1_128"
    GTIN = "gtin"
    ISBN = "isbn"
    ISBN10 = "isbn10"
    ISBN13 = "isbn13"
    ISSN = "issn"
    ITF = "itf"
    JAN = "jan"
    NW_7 = "nw-7"
    PZN = "pzn"
    UPC = "upc"
    UPCA = "upca"


DEFAULT_BARCODE_TYPE = BarcodeType.CODE128


class Direction(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class Output(str, Enum):
    BROWSER = "browser"
    CONSOLE = "console"
    CONSOLE_INVERTED = "console-inverted"
    IMAGEMAGICK = "imagemagick"
    PNG = "png"
    PRINTER = "printer"
