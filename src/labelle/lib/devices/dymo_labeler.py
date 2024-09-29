# === LICENSE STATEMENT ===
# Copyright (c) 2011 Sebastian J. Bronner <waschtl@sbronner.com>
#
# Copying and distribution of this file, with or without modification, are
# permitted in any medium without royalty provided the copyright notice and
# this notice are preserved.
# === END LICENSE STATEMENT ===
from __future__ import annotations

import array
import logging
import math
from typing import NamedTuple

import usb
from PIL import Image
from usb.core import NoBackendError, USBError

from labelle.lib.constants import ESC, SIMULATOR_CONFIG, SYN
from labelle.lib.devices.device_config import DeviceConfig
from labelle.lib.devices.device_manager import get_device_config_by_id
from labelle.lib.devices.usb_device import UsbDevice, UsbDeviceError
from labelle.lib.render_engines.margins import LabelMarginsPx

LOG = logging.getLogger(__name__)
POSSIBLE_USB_ERRORS = (UsbDeviceError, NoBackendError, USBError)


class DymoLabelerDetectError(Exception):
    def __init__(self, error: str):
        msg = f"Detection error: {error}"
        super().__init__(msg)


class DymoLabelerPrintError(Exception):
    def __init__(self, error: str):
        msg = f"Print error: {error}"
        super().__init__(msg)


class DymoLabelerFunctions:
    """Create and work with a Dymo LabelManager PnP object.

    This class contains both mid-level and high-level functions. In general,
    the high-level functions should be used. However, special purpose usage
    may require the mid-level functions. That is why they are provided.
    However, they should be well understood before use. Look at the
    high-level functions for help. Each function is marked in its docstring
    with 'HLF' or 'MLF' in parentheses.

    A partial reference of the protocol is the Technical Reference for the
    LabelWriter 450:
    <https://download.dymo.com/dymo/technical-data-sheets/LW%20450%20Series%20Technical%20Reference.pdf>
    """

    # Max number of print lines to send before waiting for a response. This helps
    # to avoid timeouts due to differences between data transfer and
    # printer speeds. I added this because I kept getting "IOError: [Errno
    # 110] Connection timed out" with long labels. Using dev.default_timeout
    # (1000) and the transfer speeds available in the descriptors somewhere, a
    # sensible timeout can also be calculated dynamically.
    _synwait: int | None
    _bytesPerLine: int | None
    _devout: usb.core.Endpoint
    _devin: usb.core.Endpoint

    def __init__(
        self,
        devout: usb.core.Endpoint,
        devin: usb.core.Endpoint,
        synwait: int | None = None,
    ):
        """Initialize the LabelManager object (HLF)."""
        self._cmd: list[int] = []
        self._response = False
        self._bytesPerLine = None
        self._dotTab = 0
        self._maxLines = 200
        self._devout = devout
        self._devin = devin
        self._synwait = synwait

    @classmethod
    def _max_bytes_per_line(cls, tape_size_mm: int) -> int:
        return int(8 * tape_size_mm / 12)

    @classmethod
    def height_px(cls, tape_size_mm: int):
        return cls._max_bytes_per_line(tape_size_mm) * 8

    def _send_command(self):
        """Send the already built command to the LabelManager (MLF)."""
        if len(self._cmd) == 0:
            return None

        while len(self._cmd) > 0:
            if self._synwait is None:
                cmd_to_send = self._cmd
                cmd_rest = []
            else:
                # Send a status request
                cmdBin = array.array("B", [ESC, ord("A")])
                cmdBin.tofile(self._devout)
                rspBin = self._devin.read(8)
                _ = array.array("B", rspBin).tolist()
                # Ok, we got a response. Now we can send a chunk of data

                # Compute a chunk with at most synwait SYN characters
                synCount = 0  # Number of SYN characters encountered in iteration
                pos = -1  # Index of last SYN character encountered in iteration
                while synCount < self._synwait:
                    try:
                        # Increment pos to the index of the next SYN character
                        pos += self._cmd[pos + 1 :].index(SYN) + 1
                        synCount += 1
                    except ValueError:
                        # No more SYN characters in cmd
                        pos = len(self._cmd)
                        break
                cmd_to_send = self._cmd[:pos]
                cmd_rest = self._cmd[pos:]
                LOG.debug(f"Sending chunk of {len(cmd_to_send)} bytes")

            # Remove the computed chunk from the command to be processed
            self._cmd = cmd_rest

            # Send the chunk
            cmdBin = array.array("B", cmd_to_send)
            cmdBin.tofile(self._devout)

        self._cmd = []  # This looks redundant.
        if not self._response:
            return None
        self._response = False
        responseBin = self._devin.read(8)
        response = array.array("B", responseBin).tolist()
        return response

    def _reset_command(self) -> None:
        """Remove a partially built command (MLF)."""
        self._cmd = []
        self._response = False

    def _build_command(self, cmd):
        """Add the next instruction to the command (MLF)."""
        self._cmd += cmd

    def _status_request(self) -> None:
        """Set instruction to get the device's status (MLF)."""
        cmd = [ESC, ord("A")]
        self._build_command(cmd)
        self._response = True

    def _dot_tab(self, value, tape_size_mm: int) -> None:
        """Set the bias text height, in bytes (MLF)."""
        if value < 0 or value > self._max_bytes_per_line(tape_size_mm):
            raise ValueError
        cmd = [ESC, ord("B"), value]
        self._build_command(cmd)
        self._dotTab = value
        self._bytesPerLine = None

    def _tape_color(self, value):
        """Set the tape color (MLF)."""
        if value < 0:
            raise ValueError
        cmd = [ESC, ord("C"), value]
        self._build_command(cmd)

    def _bytes_per_line(self, value: int):
        """Set the number of bytes sent in the following lines (MLF)."""
        if value == self._bytesPerLine:
            return
        cmd = [ESC, ord("D"), value]
        self._build_command(cmd)
        self._bytesPerLine = value

    def _cut(self) -> None:
        """Set instruction to trigger cutting of the tape (MLF)."""
        cmd = [ESC, ord("E")]
        self._build_command(cmd)

    def _line(self, value) -> None:
        """Set next printed line (MLF)."""
        self._bytes_per_line(len(value))
        cmd = [SYN, *value]
        self._build_command(cmd)

    def _chain_mark(self, tape_size_mm: int) -> None:
        """Set Chain Mark (MLF)."""
        self._dot_tab(0, tape_size_mm)
        self._bytes_per_line(self._max_bytes_per_line(tape_size_mm))
        self._line([0x99] * self._max_bytes_per_line(tape_size_mm))

    def _skip_lines(self, value) -> None:
        """Set number of lines of white to print (MLF)."""
        if value <= 0:
            raise ValueError
        self._bytes_per_line(0)
        cmd = [SYN] * value
        self._build_command(cmd)

    def _init_label(self) -> None:
        """Set the label initialization sequence (MLF).

        This was in the original dymoprint by S. Bronner but was never invoked.
        (There was a self.initLabel without parentheses.)
        I see no mention of it in the technical reference, so this seems to be
        dead code.
        """
        cmd = [0x00] * 8
        self._build_command(cmd)

    def _get_status(self):
        """Ask for and return the device's status (HLF)."""
        self._status_request()
        return self._send_command()

    def print_label(self, lines: list[list[int]]):
        """Print the label described by lines.

        Automatically split the label if it's larger than maxLines.
        """
        while len(lines) > self._maxLines + 1:
            self._raw_print_label(lines[0 : self._maxLines])
            del lines[0 : self._maxLines]
        self._raw_print_label(lines)

    def _raw_print_label(self, lines: list[list[int]]):
        """Print the label described by lines (HLF)."""
        # Here used to be a matrix optimization code that caused problems in issue #87
        self._tape_color(0)
        for line in lines:
            self._line(line)
        self._status_request()
        status = self._get_status()
        LOG.debug(f"Post-send response: {status}")


class TapePrintProperties(NamedTuple):
    usable_tape_height_px: int
    top_margin_px: int
    bottom_margin_px: int


class DymoLabeler:
    _device: UsbDevice | None
    device_config: DeviceConfig
    tape_size_mm: int

    def __init__(
        self,
        tape_size_mm: int | None = None,
        device: UsbDevice | None = None,
    ):
        self.set_device(device)

        if self.device_config is None:
            raise ValueError("No device config")

        if tape_size_mm is None:
            # Select highest supported tape size as default, if not set
            tape_size_mm = max(self.device_config.supported_tape_sizes_mm)

        # Check if selected tape size is supported
        if tape_size_mm not in self.device_config.supported_tape_sizes_mm:
            raise ValueError(
                f"Unsupported tape size {tape_size_mm}mm. "
                f"Supported sizes: {self.device_config.supported_tape_sizes_mm}mm"
            )
        self.tape_size_mm = tape_size_mm

    def get_label_height_px(self):
        """Get the (usable) tape height in pixels."""
        return self.tape_print_properties.usable_tape_height_px

    @property
    def minimum_horizontal_margin_mm(self):
        # Return distance between printhead and cutter
        # as we don't want to cut though our printed label
        return self.px_to_mm(
            self.device_config.distance_between_print_head_and_cutter_px
        )

    def get_labeler_margin_px(self) -> LabelMarginsPx:
        return LabelMarginsPx(
            horizontal=self.device_config.distance_between_print_head_and_cutter_px,
            vertical=self.tape_print_properties.top_margin_px,
        )

    @property
    def tape_print_properties(self) -> TapePrintProperties:
        # Check if selected tape size supported
        if self.tape_size_mm not in self.device_config.supported_tape_sizes_mm:
            raise ValueError(
                f"Unsupported tape size {self.tape_size_mm}mm. "
                f"Supported sizes: {self.device_config.supported_tape_sizes_mm}mm"
            )

        # Calculate usable tape height (*2 for top and bottom)
        usable_tape_height_mm: float = self.tape_size_mm - (
            2 * self.device_config.tape_alignment_inaccuracy_mm
        )

        # Calculate the numer of active pixels for the tape
        usable_tape_height_pixels: float = 0
        if usable_tape_height_mm >= self.device_config.print_head_mm:
            # Tape is larger than active area of printhead. Use all pixels
            usable_tape_height_pixels = self.device_config.print_head_px
        else:
            # Calculate the amount of active pixels we are able to use
            # (taking the placement inaccuracy into account)
            usable_tape_height_pixels = self.pixels_per_mm() * usable_tape_height_mm

        # Round down to nearest whole number as we can't use half a pixels ;)
        usable_tape_height_pixels = math.floor(usable_tape_height_pixels)

        # To calculate the margins we need to know some hardware info:
        # The printer has special "support studs" that allow 19 & 24mm tapes
        # to sink to the bottom of the printer.
        # 12mm based casettes are raised slightly so they are center to the printhead.
        # Tapes smaller than 12mm are centered in the cartridge and to the printhead.
        # This gives us the advantage that we can calculate the top and bottom margin

        # Calculate the top margin
        margin_top = round(
            ((self.device_config.print_head_px - usable_tape_height_pixels) / 2), 0
        )

        # Bottom margin is equal due to centering of the tape
        margin_bottom = margin_top

        # Make sure the total is the exact amount of pixels of the printhead
        # Aka compensate for margin rounding/division errors
        usable_tape_height_pixels = self.device_config.print_head_px - (
            margin_top + margin_bottom
        )

        # Return active pixels / margins set
        return TapePrintProperties(
            usable_tape_height_px=int(usable_tape_height_pixels),
            top_margin_px=int(margin_top),
            bottom_margin_px=int(margin_bottom),
        )

    @property
    def device(self) -> UsbDevice | None:
        # Using a property here shields the device from being mutated
        # outside of set_device.
        return self._device

    def set_device(self, device: UsbDevice | None):
        try:
            if device is not None:
                device.setup()

                # Retrieve device config based on product ID
                self.device_config = get_device_config_by_id(device.id_product)
            else:
                # Use simulator config
                self.device_config = SIMULATOR_CONFIG

        except UsbDeviceError as e:
            device = None
            LOG.error(e)
        self._device = device

    @property
    def is_ready(self) -> bool:
        return self.device is not None

    def pixels_per_mm(self) -> float:
        # Calculate the pixels per mm for this printer
        # Example: printhead of 128 Pixels, distributed over 18 mm of active area.
        #   Makes 7.11 pixels/mm
        return self.device_config.print_head_px / self.device_config.print_head_mm

    def px_to_mm(self, px: int) -> float:
        """Convert pixels to millimeters for the current printer."""
        mm = px / self.pixels_per_mm()
        # Round up to nearest 0.1mm
        return math.ceil(mm * 10) / 10

    def mm_to_px(self, mm: float) -> int:
        """Convert millimeters to pixels for the current printer."""
        return math.ceil(mm * self.pixels_per_mm())

    def print(
        self,
        bitmap: Image.Image,
    ) -> None:
        """Print a label bitmap to the detected printer.

        The label bitmap is a PIL image in 1-bit format (mode=1), and pixels with value
        equal to 1 are burned.
        """
        # Convert the image to the proper matrix for the dymo labeler object so that
        # rows span the width of the label, and the first row corresponds to the left
        # edge of the label.
        rotated_bitmap = bitmap.transpose(Image.Transpose.ROTATE_270)

        # Convert the image to raw bytes. Pixels along rows are chunked into groups of
        # 8 pixels, and subsequent rows are concatenated.
        stream: bytes = rotated_bitmap.tobytes()

        # Regather the bytes into rows
        stream_row_length = int(math.ceil(bitmap.height / 8))
        if len(stream) // stream_row_length != bitmap.width:
            raise RuntimeError(
                "An internal problem was encountered while processing the "
                "label bitmap!"
            )
        label_rows: list[bytes] = [
            stream[i : i + stream_row_length]
            for i in range(0, len(stream), stream_row_length)
        ]

        # Convert bytes into ints
        label_matrix: list[list[int]] = [
            array.array("B", label_row).tolist() for label_row in label_rows
        ]

        try:
            LOG.debug("Printing label..")
            assert self._device is not None
            functions = DymoLabelerFunctions(
                devout=self._device.devout,
                devin=self._device.devin,
                synwait=64,
            )
            functions.print_label(label_matrix)
            LOG.debug("Done printing.")
            if self._device is not None:
                self._device.dispose()
            LOG.debug("Cleaned up.")
        except POSSIBLE_USB_ERRORS as e:
            raise DymoLabelerPrintError(str(e)) from e
