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
from enum import Enum, IntEnum
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


# Supported USB device ID enumeration
class SUPPORTED_DEVICE_ID(IntEnum):
    LABELMANAGER_PC = 0x0011
    LABELPOINT_350 = 0x0015
    LABELMANAGER_PC_II = 0x001C
    LABELMANAGER_PNP_NO_MODE_SWITCH = 0x1001
    LABELMANAGER_PNP_MODE_SWITCH = 0x1002
    LABELMANAGER_420P_NO_MODE_SWITCH = 0x1003
    LABELMANAGER_420P_MODE_SWITCH = 0x1004
    LABELMANAGER_280P_NO_MODE_SWITCH = 0x1005
    LABELMANAGER_280P_MODE_SWITCH = 0x1006
    LABELMANAGER_WIRELESS_PNP_NO_MODE_SWITCH = 0x1007
    LABELMANAGER_WIRELESS_PNP_MODE_SWITCH = 0x1008
    MOBILE_LABELER = 0x1009


# Create supported products list
SUPPORTED_PRODUCTS = []

# ---- Supported USB Devices configuration ----
SUPPORTED_PRODUCTS.append(
    DeviceConfig(
        "DYMO LabelMANAGER PC",
        [int(SUPPORTED_DEVICE_ID.LABELMANAGER_PC)],
        # ToDo: Validate config!
        128,
        [6, 9, 12, 19],
        {6: (44, 85), 9: (31, 94), 12: (38, 117), 19: (2, 127)},
    )
)
SUPPORTED_PRODUCTS.append(
    DeviceConfig(
        "LabelPoint 350",
        [int(SUPPORTED_DEVICE_ID.LABELPOINT_350)],
        # ToDo: Validate config!
        64,
        [6, 9, 12],
        {6: (44, 85), 9: (31, 94), 12: (38, 117)},
    )
)
SUPPORTED_PRODUCTS.append(
    DeviceConfig(
        "DYMO LabelMANAGER PC II",
        [int(SUPPORTED_DEVICE_ID.LABELMANAGER_PC_II)],
        128,
        [6, 9, 12, 19, 24],
        {6: (44, 85), 9: (31, 94), 12: (38, 117), 19: (2, 127), 24: (2, 127)},
    )
)
SUPPORTED_PRODUCTS.append(
    DeviceConfig(
        "LabelManager PnP",
        [
            int(SUPPORTED_DEVICE_ID.LABELMANAGER_PNP_NO_MODE_SWITCH),
            int(SUPPORTED_DEVICE_ID.LABELMANAGER_PNP_MODE_SWITCH),
        ],
        # ToDo: Validate config!
        64,
        [6, 9, 12],
        {6: (44, 85), 9: (31, 94), 12: (38, 117)},
    )
)
SUPPORTED_PRODUCTS.append(
    DeviceConfig(
        f"LabelManager 420P {UNCONFIRMED_MESSAGE}",
        [
            int(SUPPORTED_DEVICE_ID.LABELMANAGER_420P_NO_MODE_SWITCH),
            int(SUPPORTED_DEVICE_ID.LABELMANAGER_420P_MODE_SWITCH),
        ],
        # ToDo: Validate config!
        64,
        [6, 9, 12],
        {6: (44, 85), 9: (31, 94), 12: (38, 117)},
    )
)
SUPPORTED_PRODUCTS.append(
    DeviceConfig(
        "LabelManager 280",
        [
            int(SUPPORTED_DEVICE_ID.LABELMANAGER_280P_MODE_SWITCH),
            int(SUPPORTED_DEVICE_ID.LABELMANAGER_280P_NO_MODE_SWITCH),
        ],
        # ToDo: Validate config!
        64,
        [6, 9, 12],
        {6: (44, 85), 9: (31, 94), 12: (38, 117)},
    )
)
SUPPORTED_PRODUCTS.append(
    DeviceConfig(
        f"LabelManager Wireless PnP {UNCONFIRMED_MESSAGE}",
        [
            int(SUPPORTED_DEVICE_ID.LABELMANAGER_WIRELESS_PNP_NO_MODE_SWITCH),
            int(SUPPORTED_DEVICE_ID.LABELMANAGER_WIRELESS_PNP_MODE_SWITCH),
        ],
        # ToDo: Validate config!
        64,
        [6, 9, 12],
        {6: (44, 85), 9: (31, 94), 12: (38, 117)},
    )
)
SUPPORTED_PRODUCTS.append(
    DeviceConfig(
        f"MobileLabeler {UNCONFIRMED_MESSAGE}",
        [int(SUPPORTED_DEVICE_ID.MOBILE_LABELER)],
        # ToDo: Validate config!
        64,
        [6, 9, 12],
        {6: (44, 85), 9: (31, 94), 12: (38, 117)},
    )
)

# Simulator configuration
SIMULATOR_CONFIG = DeviceConfig(
    "Simulator",
    [0],
    128,
    [6, 9, 12, 19, 24],
    {6: (44, 85), 9: (31, 94), 12: (38, 117), 19: (2, 127), 24: (2, 127)},
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
