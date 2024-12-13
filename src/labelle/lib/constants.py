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
SUPPORTED_PRODUCTS = {
    0x0011: "DYMO LabelMANAGER PC",
    0x0015: "LabelPoint 350",
    0x0016: f"Rhino 6000+ {UNCONFIRMED_MESSAGE}",
    0x1001: "LabelManager PnP (no mode switch)",
    0x1002: "LabelManager PnP (mode switch)",
    0x1003: f"LabelManager 420P (no mode switch) {UNCONFIRMED_MESSAGE}",
    0x1004: f"LabelManager 420P (mode switch) {UNCONFIRMED_MESSAGE}",
    0x1005: "LabelManager 280 (no mode switch)",
    0x1006: "LabelManager 280 (no mode switch)",
    0x1007: f"LabelManager Wireless PnP (no mode switch) {UNCONFIRMED_MESSAGE}",
    0x1008: f"LabelManager Wireless PnP (mode switch) {UNCONFIRMED_MESSAGE}",
    0x1009: f"MobileLabeler {UNCONFIRMED_MESSAGE}",
}
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
