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
import random
import struct
import time
from dataclasses import dataclass

import usb
from PIL import Image
from usb.core import NoBackendError, USBError

from labelle.lib.constants import (
    DPI,
    ESC,
    MOBILE_LABELER_DPI,
    PRODUCT_MOBILE_LABELER,
    SYN,
)
from labelle.lib.devices.serial_device import SerialDevice, SerialDeviceError
from labelle.lib.devices.usb_device import UsbDevice, UsbDeviceError
from labelle.lib.utils import mm_to_px, px_to_mm

LOG = logging.getLogger(__name__)
POSSIBLE_USB_ERRORS = (UsbDeviceError, SerialDeviceError, NoBackendError, USBError)


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


@dataclass(frozen=True)
class MobileLabelerTape:
    """Raster geometry of one tape width on the DYMO MobileLabeler (300 dpi).

    Each raster line (one column across the tape, sent bottom edge first) is
    ``line_bytes`` long.  The print head only covers the first ``height_px`` bits;
    the remaining ``skip_px`` bits (the top edge of the tape) are not printed.
    """

    line_bytes: int
    height_px: int
    verified: bool = False

    @property
    def skip_px(self) -> int:
        return self.line_bytes * 8 - self.height_px


# 24 mm was measured on real hardware: the print head is 256 dots wide and lines of
# 36 bytes (as sent by DYMO's own CUPS driver) lose their last 32 bits.  The other
# widths follow the page widths of DYMO's lmmls.ppd and are not yet verified.
MOBILE_LABELER_TAPES: dict[int, MobileLabelerTape] = {
    6: MobileLabelerTape(line_bytes=10, height_px=75),
    9: MobileLabelerTape(line_bytes=14, height_px=108),
    12: MobileLabelerTape(line_bytes=19, height_px=146),
    19: MobileLabelerTape(line_bytes=29, height_px=229),
    24: MobileLabelerTape(line_bytes=36, height_px=256, verified=True),
}

# Media IDs reported in the status block, per tape width
# (from DYMO's CLabelManagerLanguageMonitorV2::GetTapeWidthFromMediaType).
_MOBILE_LABELER_MEDIA_IDS: dict[int, tuple[int, ...]] = {
    6: (4, 9, 14, 22, 43610, 43613, 43618),
    9: (5, 10, 15, 23, 40910, 40914, 40915, 40916, 40917, 40918, 40919),
    12: (3, 8, 13, 21, *range(45010, 45022), 16957, 16959),
    19: (2, 7, 12, 20, 45800, *range(45803, 45812), 16958, 16960),
    24: (1, 6, 11, 19, 53710, *range(53713, 53722)),
}


@dataclass(frozen=True)
class MobileLabelerStatus:
    raw: bytes

    @property
    def print_status(self) -> int:
        return self.raw[0] & 0x3

    @property
    def job_id(self) -> int:
        return struct.unpack_from("<I", self.raw, 1)[0]

    @property
    def cutter_status(self) -> int:
        return self.raw[7] & 0x7

    @property
    def head_status(self) -> int:
        return self.raw[8] & 0x3

    @property
    def bay_status(self) -> int:
        return self.raw[10] & 0xF

    @property
    def media_id(self) -> int:
        return struct.unpack_from("<I", self.raw, 11)[0]

    @property
    def battery_status(self) -> int:
        return self.raw[21]

    @property
    def error_id(self) -> int:
        return struct.unpack_from("<I", self.raw, 23)[0]

    @property
    def tape_size_mm(self) -> int | None:
        for size_mm, ids in _MOBILE_LABELER_MEDIA_IDS.items():
            if self.media_id in ids:
                return size_mm
        return None

    @property
    def is_busy(self) -> bool:
        return self.print_status == 1 or self.cutter_status in (2, 3)

    def problem(self) -> str | None:
        """Return a description of what prevents printing, or None."""
        if self.print_status == 2:
            return "general printer error"
        if self.bay_status <= 3:
            return "no tape cassette inserted, or it is not recognized"
        if self.bay_status == 5:
            return "tape is used up"
        if self.cutter_status == 4 or self.bay_status == 9:
            return "cutter or tape slot error"
        if self.head_status == 1:
            return "print head is overheated"
        if self.battery_status == 4:
            return "battery is too low"
        if self.error_id:
            return f"printer reports error 0x{self.error_id:x}"
        return None

    def __str__(self) -> str:
        return (
            f"print={self.print_status} job={self.job_id} "
            f"cutter={self.cutter_status} head={self.head_status} "
            f"bay={self.bay_status} media={self.media_id} "
            f"battery={self.battery_status} error=0x{self.error_id:x}"
        )


class MobileLabelerFunctions:
    """DYMO MobileLabeler, which speaks the "LabelManager V2" protocol.

    Reference: DYMO's GPL CUPS driver, LW5xx_Linux/src/lm in
    <https://github.com/dymosoftware/Drivers>.
    """

    STATUS_LENGTH = 28
    # The printer feeds the head-to-cutter distance by itself before printing,
    # and a form feed moves the end of the label past the cutter.
    LEADER_PX = 0
    TRAILER_PX = 0

    def __init__(
        self,
        devout: usb.core.Endpoint | SerialDevice,
        devin: usb.core.Endpoint | SerialDevice,
        supports_status: bool = True,
    ):
        self._devout = devout
        self._devin = devin
        self._supports_status = supports_status

    def get_status(self, lock: bool = False) -> MobileLabelerStatus:
        self._devout.write(bytes([ESC, ord("A"), int(lock)]), 2000)
        raw = bytes(self._devin.read(64, 3000))
        if len(raw) != self.STATUS_LENGTH:
            raise DymoLabelerPrintError(f"Unexpected status reply: {raw.hex(' ')}")
        status = MobileLabelerStatus(raw)
        LOG.debug(f"Status: {status}")
        return status

    def _wait_until_idle(self, timeout_s: float) -> MobileLabelerStatus | None:
        deadline = time.monotonic() + timeout_s
        status = None
        while time.monotonic() < deadline:
            time.sleep(0.5)
            try:
                status = self.get_status()
            except USBError:
                # The printer does not answer while it is printing or cutting.
                continue
            if not status.is_busy:
                return status
        return status

    @staticmethod
    def build_job(lines: list[bytes], line_bytes: int, cut: bool = True) -> bytes:
        job = bytearray()
        job += bytes([ESC, ord("s")]) + struct.pack("<I", random.getrandbits(31))
        job += bytes([ESC, ord("n")]) + struct.pack("<H", 1)
        job += bytes([ESC, ord("l")]) + struct.pack(
            "<I", MobileLabelerFunctions.LEADER_PX
        )
        job += bytes([ESC, ord("t")]) + struct.pack(
            "<I", MobileLabelerFunctions.TRAILER_PX
        )
        job += bytes([ESC, ord("D"), 0x01, 0x02])
        job += struct.pack("<II", len(lines), line_bytes * 8)
        job += b"".join(lines)
        job += bytes([ESC, ord("E")])
        if cut:
            job += bytes([ESC, ord("p"), 0x30])
        job += bytes([ESC, ord("Q")])
        return bytes(job)

    def print_label(self, lines: list[bytes], line_bytes: int) -> None:
        if not self._supports_status:
            # Over Bluetooth the printer accepts jobs but never replies.
            job = self.build_job(lines, line_bytes)
            LOG.debug(
                f"Sending job of {len(lines)} lines, {len(job)} bytes (no status)"
            )
            self._devout.write(job, 30000)
            return
        status = self.get_status(lock=True)
        if status.is_busy:
            status = self._wait_until_idle(30) or status
        problem = status.problem()
        if problem:
            raise DymoLabelerPrintError(problem)
        job = self.build_job(lines, line_bytes)
        LOG.debug(f"Sending job of {len(lines)} lines, {len(job)} bytes")
        self._devout.write(job, 30000)
        final = self._wait_until_idle(60)
        if final is None:
            raise DymoLabelerPrintError("No status from printer after printing")
        problem = final.problem()
        if problem:
            raise DymoLabelerPrintError(problem)
        LOG.debug(f"Post-print status: {final}")


class DymoLabeler:
    _device: UsbDevice | SerialDevice | None
    tape_size_mm: int

    LABELER_DISTANCE_BETWEEN_PRINT_HEAD_AND_CUTTER_MM = 8.1
    LABELER_PRINT_HEAD_HEIGHT_MM = 8.2
    SUPPORTED_TAPE_SIZES_MM = (19, 12, 9, 6)
    DEFAULT_TAPE_SIZE_MM = 12

    MOBILE_LABELER_SUPPORTED_TAPE_SIZES_MM = (24, 19, 12, 9, 6)

    def __init__(
        self,
        tape_size_mm: int | None = None,
        device: UsbDevice | SerialDevice | None = None,
    ):
        self._device = device
        if tape_size_mm is None:
            tape_size_mm = self.DEFAULT_TAPE_SIZE_MM
        self.tape_size_mm = tape_size_mm
        self.check_tape_size()

    def check_tape_size(self) -> None:
        if self.tape_size_mm not in self.supported_tape_sizes_mm:
            raise ValueError(
                f"Unsupported tape size {self.tape_size_mm}mm. "
                f"Supported sizes: {self.supported_tape_sizes_mm}"
            )

    @property
    def is_mobile_labeler(self) -> bool:
        return (
            self._device is not None
            and self._device.id_product == PRODUCT_MOBILE_LABELER
        )

    @property
    def supported_tape_sizes_mm(self) -> tuple[int, ...]:
        if self.is_mobile_labeler:
            return self.MOBILE_LABELER_SUPPORTED_TAPE_SIZES_MM
        return self.SUPPORTED_TAPE_SIZES_MM

    @property
    def dpi(self) -> int:
        return MOBILE_LABELER_DPI if self.is_mobile_labeler else DPI

    @property
    def _mobile_tape(self) -> MobileLabelerTape:
        return MOBILE_LABELER_TAPES[self.tape_size_mm]

    @property
    def height_px(self):
        if self.is_mobile_labeler:
            return self._mobile_tape.height_px
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
    def _mobile_functions(self) -> MobileLabelerFunctions:
        assert self._device is not None
        return MobileLabelerFunctions(
            devout=self._device.devout,
            devin=self._device.devin,
            supports_status=getattr(self._device, "supports_status", True),
        )

    def detect_tape_size_mm(self) -> int | None:
        """Ask the printer which tape is loaded (MobileLabeler only)."""
        if not self.is_mobile_labeler or not getattr(
            self._device, "supports_status", True
        ):
            return None
        try:
            status = self._mobile_functions.get_status()
        except (*POSSIBLE_USB_ERRORS, DymoLabelerPrintError) as e:
            LOG.debug(f"Could not read tape size: {e}")
            return None
        return status.tape_size_mm

    @property
    def minimum_horizontal_margin_mm(self):
        return self.LABELER_DISTANCE_BETWEEN_PRINT_HEAD_AND_CUTTER_MM

    @property
    def labeler_margin_px(self) -> tuple[float, float]:
        vertical_margin_mm = max(
            0, (self.tape_size_mm - self.LABELER_PRINT_HEAD_HEIGHT_MM) / 2
        )
        if self.is_mobile_labeler:
            vertical_margin_mm = max(
                0.0, (self.tape_size_mm - px_to_mm(self.height_px, self.dpi)) / 2
            )

        return (
            mm_to_px(self.minimum_horizontal_margin_mm, self.dpi),
            mm_to_px(vertical_margin_mm, self.dpi),
        )

    @property
    def device(self) -> UsbDevice | SerialDevice | None:
        return self._device

    @device.setter
    def device(self, device: UsbDevice | SerialDevice | None):
        try:
            if device:
                device.setup()
        except UsbDeviceError as e:
            device = None
            LOG.error(e)
        self._device = device
        if self.tape_size_mm not in self.supported_tape_sizes_mm:
            self.tape_size_mm = self.DEFAULT_TAPE_SIZE_MM

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
        # Convert the image to the proper matrix for the dymo labeler object so that
        # rows span the width of the label, and the first row corresponds to the left
        # edge of the label.
        rotated_bitmap = bitmap.transpose(Image.Transpose.ROTATE_270)

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
            stream[i : i + stream_row_length]
            for i in range(0, len(stream), stream_row_length)
        ]

        try:
            LOG.debug("Printing label..")
            if self.is_mobile_labeler:
                self._print_mobile(bitmap)
            else:
                # Convert bytes into ints
                label_matrix: list[list[int]] = [
                    array.array("B", label_row).tolist() for label_row in label_rows
                ]
                self._functions.print_label(label_matrix)
            LOG.debug("Done printing.")
            if self._device is not None:
                self._device.dispose()
            LOG.debug("Cleaned up.")
        except POSSIBLE_USB_ERRORS as e:
            raise DymoLabelerPrintError(str(e)) from e

    def _print_mobile(self, bitmap: Image.Image) -> None:
        tape = self._mobile_tape
        if not tape.verified:
            LOG.warning(
                f"MobileLabeler: {self.tape_size_mm}mm tape geometry is not verified "
                "on real hardware yet; the print may be offset vertically."
            )
        # labelle's margin model (see MarginsRenderEngine) starts the bitmap one
        # head-to-cutter distance early and ends it one distance late.  The
        # MobileLabeler feeds that distance by itself before printing and again in
        # the form feed after it, so the end of the bitmap is two distances too long
        # (measured: 8 mm left vs. 16 mm right when only one was removed).  Trim that
        # blank tail, but never anything that is printed.
        excess_px = round(2 * self.labeler_margin_px[0])
        ink_bbox = bitmap.getbbox()
        blank_tail_px = bitmap.width - (ink_bbox[2] if ink_bbox else 0)
        trim_px = min(excess_px, blank_tail_px)
        if trim_px > 0:
            bitmap = bitmap.crop((0, 0, bitmap.width - trim_px, bitmap.height))
        # Place the payload so that it lands on the bits the print head covers.
        canvas = Image.new("1", (bitmap.width, tape.line_bytes * 8), 0)
        canvas.paste(
            bitmap.crop((0, 0, bitmap.width, tape.height_px)), (0, tape.skip_px)
        )
        stream = canvas.transpose(Image.Transpose.ROTATE_270).tobytes()
        lines = [
            stream[i : i + tape.line_bytes]
            for i in range(0, len(stream), tape.line_bytes)
        ]
        self._mobile_functions.print_label(lines, tape.line_bytes)
