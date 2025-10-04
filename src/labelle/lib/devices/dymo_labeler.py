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

import usb
from PIL import Image
from usb.core import NoBackendError, USBError

from labelle.lib.constants import ESC, SYN
from labelle.lib.devices.usb_device import UsbDevice, UsbDeviceError
from labelle.lib.utils import mm_to_px

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
                rspBin = self._devin.read(512)
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
        responseBin = self._devin.read(512)
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


class DymoLabeler:
    _device: UsbDevice | None
    tape_size_mm: int

    LABELER_DISTANCE_BETWEEN_PRINT_HEAD_AND_CUTTER_MM = 8.1
    LABELER_PRINT_HEAD_HEIGHT_MM = 8.2
    SUPPORTED_TAPE_SIZES_MM = (24, 19, 12, 9, 6)
    DEFAULT_TAPE_SIZE_MM = 12

    def __init__(
        self,
        tape_size_mm: int | None = None,
        device: UsbDevice | None = None,
    ):
        if tape_size_mm is None:
            tape_size_mm = self.DEFAULT_TAPE_SIZE_MM
        if tape_size_mm not in self.SUPPORTED_TAPE_SIZES_MM:
            raise ValueError(
                f"Unsupported tape size {tape_size_mm}mm. "
                f"Supported sizes: {self.SUPPORTED_TAPE_SIZES_MM}"
            )
        self.tape_size_mm = tape_size_mm
        self._device = device

    @property
    def height_px(self):
        return DymoLabelerFunctions.height_px(self.tape_size_mm)

    @property
    def _functions(self) -> DymoLabelerFunctions:
        assert self._device is not None
        return DymoLabelerFunctions(
            devout=self._device.devout,
            devin=self._device.devin,
            synwait=64,
        )

    @property
    def minimum_horizontal_margin_mm(self):
        return self.LABELER_DISTANCE_BETWEEN_PRINT_HEAD_AND_CUTTER_MM

    @property
    def labeler_margin_px(self) -> tuple[float, float]:
        vertical_margin_mm = max(
            0, (self.tape_size_mm - self.LABELER_PRINT_HEAD_HEIGHT_MM) / 2
        )

        return (
            mm_to_px(self.minimum_horizontal_margin_mm),
            mm_to_px(vertical_margin_mm),
        )

    @property
    def device(self) -> UsbDevice | None:
        return self._device

    @device.setter
    def device(self, device: UsbDevice | None):
        try:
            if device:
                device.setup()
        except UsbDeviceError as e:
            device = None
            LOG.error(e)
        self._device = device

    @property
    def is_ready(self) -> bool:
        return self.device is not None

    def print(
        self,
        bitmap: Image.Image,
    ) -> None:
        """Print a label bitmap to the detected printer.

        The label bitmap is a PIL image in 1-bit format (mode=1), and pixels with value
        equal to 1 are burned.
        """

        def mirror_byte(byte):
            mirrored = 0
            for i in range(8):
                mirrored = (mirrored << 1) | (byte & 1)  # Shift mirrored left and add LSB of byte
                byte >>= 1  # Shift byte right
            return mirrored

        # Convert the image to the proper matrix for the dymo labeler object so that
        # rows span the width of the label, and the first row corresponds to the left
        # edge of the label.
        rotated_bitmap = bitmap.transpose(Image.Transpose.ROTATE_270)
        rotated_bitmap = rotated_bitmap.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

        # Convert the image to raw bytes. Pixels along rows are chunked into groups of
        # 8 pixels, and subsequent rows are concatenated.
        stream: bytes = rotated_bitmap.tobytes()

        # Regather the bytes into rows
        stream_row_length = math.ceil(bitmap.height / 8)
        if len(stream) // stream_row_length != bitmap.width:
            raise RuntimeError(
                "An internal problem was encountered while processing the label bitmap!"
            )
        label_rows: list[bytes] = [
            bytes(mirror_byte(b) for b in stream[i: i + stream_row_length])
            for i in range(0, len(stream), stream_row_length)
        ]

        # Convert bytes into ints
        label_matrix: list[list[int]] = [
            array.array("B", label_row).tolist() for label_row in label_rows
        ]

        try:
            LOG.debug("Printing label..")
            self._functions.print_label(label_matrix)
            LOG.debug("Done printing.")
            if self._device is not None:
                self._device.dispose()
            LOG.debug("Cleaned up.")
        except POSSIBLE_USB_ERRORS as e:
            raise DymoLabelerPrintError(str(e)) from e
