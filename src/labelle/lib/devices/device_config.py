from __future__ import annotations

import logging
from typing import Tuple

LOG = logging.getLogger(__name__)


class DeviceConfig:
    """Configuration object for the capabilities of a label printer."""

    name: str
    """Name of this device"""

    deviceIDs: list[int]
    """List of USB Device ID's this device can identify as"""

    printHeadSizePixels: int
    """Size of the print head in pixels (use calibration routine to determine)"""

    supportedTapeSizes: list[int]
    """List of supported tape sizes in mm"""

    marginsPerTape: dict[int, Tuple[int, int]]
    """
    Dictonary of print margins per tape size
    Entry: TapeSizeMM : (topMarginInPx, bottomMarginInPx)
    Use the calibration routine to determine these for each tape size
    """

    def __init__(
        self,
        name: str,
        deviceIDs: list[int],
        printHeadSizePixels: int,
        supportedTapeSizes: list[int],
        marginsPerTape: dict[int, Tuple[int, int]],
    ):
        """Initialize a Labeler config object."""
        self.name = name
        self.deviceIDs = deviceIDs
        self.printHeadSizePixels = printHeadSizePixels
        self.supportedTapeSizes = supportedTapeSizes
        self.marginsPerTape = marginsPerTape

    def matches_device_id(self, idValue: int) -> bool:
        """Check if the a device ID matches this config."""
        if idValue in self.deviceIDs:
            return True
        else:
            return False

    def get_tape_print_margins(self, tapeSizeMM: int) -> tuple[int, int]:
        """Get print margins for a specific tape size.

        :param tapeSizeMM: Tape size in mm
        :return: Margins tuple, None if not supported
        """
        if tapeSizeMM in self.supportedTapeSizes:
            if tapeSizeMM in self.marginsPerTape:
                # Return specified margins
                return self.marginsPerTape[tapeSizeMM]
            else:
                # No specific margins set, return default
                return (0, 0)
        else:
            # Tape size not supported
            raise ValueError(
                f"Unsupported tape size {tapeSizeMM}mm. "
                f"Supported sizes: {self.supportedTapeSizes}mm"
            )
