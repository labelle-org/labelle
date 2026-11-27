"""Bluetooth (serial port) connection to a DYMO MobileLabeler.

A paired MobileLabeler offers a Serial Port Profile service ("MLS DataPort"),
which the OS exposes as a serial port, e.g. ``/dev/cu.DYMOML89C6`` on macOS,
``/dev/rfcomm0`` on Linux (after ``rfcomm bind``) or ``COM5`` on Windows.

The printer accepts the same job stream as over USB, but it does not answer
status requests over Bluetooth, so tape size and error states are unknown.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from labelle.lib.constants import DEV_VENDOR, PRODUCT_MOBILE_LABELER

LOG = logging.getLogger(__name__)


class SerialDeviceError(RuntimeError):
    pass


class SerialDevice:
    """Stands in for UsbDevice; acts as its own write and read endpoint."""

    id_vendor = DEV_VENDOR
    id_product = PRODUCT_MOBILE_LABELER
    supports_status = False

    # Opening the port starts the Bluetooth connection, and data written before the
    # link is up is lost; closing the port drops the link, also losing data still
    # in flight. The printer gives no acknowledgement, so wait on both ends.
    CONNECT_SETTLE_S = 2.0
    LINGER_MIN_S = 2.0
    LINGER_BYTES_PER_S = 10_000

    def __init__(self, port: str, write_timeout_s: float = 30.0) -> None:
        self.port = port
        self._write_timeout_s = write_timeout_s
        self._serial: Any = None
        self._unsettled_bytes = 0

    @property
    def product(self) -> str:
        return f"MobileLabeler (Bluetooth, {self.port})"

    def setup(self) -> None:
        try:
            import serial
        except ImportError as e:
            raise SerialDeviceError(
                "Bluetooth printing needs pyserial: pip install 'labelle[bluetooth]'"
            ) from e
        try:
            self._serial = serial.Serial(
                self.port, timeout=3, write_timeout=self._write_timeout_s
            )
        except serial.SerialException as e:
            raise SerialDeviceError(f"Cannot open {self.port}: {e}") from e
        LOG.debug(f"Opened serial port {self.port}")
        time.sleep(self.CONNECT_SETTLE_S)

    @property
    def devout(self) -> SerialDevice:
        return self

    @property
    def devin(self) -> SerialDevice:
        return self

    def write(self, data: bytes, timeout: int | None = None) -> int:
        import serial

        assert self._serial is not None, "setup() was not called"
        try:
            written = self._serial.write(data)
            # Block until the OS has handed everything to the Bluetooth stack.
            self._serial.flush()
        except serial.SerialException as e:
            raise SerialDeviceError(f"Writing to {self.port} failed: {e}") from e
        self._unsettled_bytes += written
        return written

    def read(self, size: int, timeout: int | None = None) -> bytes:
        raise SerialDeviceError("The MobileLabeler sends no replies over Bluetooth")

    def dispose(self) -> None:
        if self._serial is not None:
            if self._unsettled_bytes:
                linger_s = max(
                    self.LINGER_MIN_S, self._unsettled_bytes / self.LINGER_BYTES_PER_S
                )
                LOG.debug(f"Waiting {linger_s:.1f}s for the printer to receive data")
                time.sleep(linger_s)
                self._unsettled_bytes = 0
            self._serial.close()
            self._serial = None
