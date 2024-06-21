from __future__ import annotations

import logging
import math

LOG = logging.getLogger(__name__)


class DeviceConfig:
    """Configuration object for the capabilities of a label printer."""

    name: str
    """Name of this device"""

    deviceIDs: list[int]
    """List of USB Device ID's this device can identify as"""

    printHeadSizePixels: int
    """Size of the print head in pixels (use calibration routine to determine)"""

    printHeadActiveAreaMillimeters: float
    """Size of the active area of the print head in millimters
        (use calibration routine to determine)"""

    supportedTapeSizes: list[int]
    """List of supported tape sizes in mm"""

    # Fixed to 1 mm until proven otherwise ;)
    TAPE_ALIGNMENT_INACCURACY_MM: float = 1
    """The inaccuracy of the tape position relative to the printhead"""
    # Inaccuracy of the tape position is mostly caused by
    # the tape moving slightly from side to side in the cartridge.
    # Improper cartrigde placemement is also an factor,
    # but negligible due to a physical spring in the lid.

    def __init__(
        self,
        name: str,
        deviceIDs: list[int],
        printHeadSizePixels: int,
        printHeadActiveAreaMillimeters: int,
        supportedTapeSizes: list[int],
    ):
        """Initialize a Labeler config object."""
        self.name = name
        self.deviceIDs = deviceIDs
        self.printHeadSizePixels = printHeadSizePixels
        self.printHeadActiveAreaMillimeters = printHeadActiveAreaMillimeters
        self.supportedTapeSizes = supportedTapeSizes

    def matches_device_id(self, idValue: int) -> bool:
        """Check if the a device ID matches this config."""
        if idValue in self.deviceIDs:
            return True
        else:
            return False

    def get_tape_print_size_and_margins_px(
        self, tapeSizeMM: int
    ) -> tuple[int, int, int]:
        """Get print margins for a specific tape size.

        :param tapeSizeMM: Tape size in mm
        :return: Margins tuple in pixels [ActivePixels,TopMarginPx,BottomMarginPx]
        """
        if tapeSizeMM in self.supportedTapeSizes:
            # Calculate the pixels per mm for this printer
            # Example: printhead of 128 Pixels, distributed over 18 mm of active area.
            #   Makes 7.11 pixels/mm
            printPPmm: float = (
                self.printHeadSizePixels / self.printHeadActiveAreaMillimeters
            )

            # Calculate usable tape width (*2 for top and bottom)
            usableTapeWidth: float = tapeSizeMM - (
                self.TAPE_ALIGNMENT_INACCURACY_MM * 2
            )

            # Calculate the numer of active pixels for the tape
            activeTapePixels: float = 0
            if usableTapeWidth >= self.printHeadActiveAreaMillimeters:
                # Tape is larger than active area of printhead. Use all pixels
                activeTapePixels = self.printHeadSizePixels
            else:
                # Calculate the amount of active pixels we are able to use
                # (taking the placement inaccuracy into account)
                activeTapePixels = printPPmm * usableTapeWidth

            # Round down to nearest whole number as we can't use half a pixels ;)
            activeTapePixels = math.floor(activeTapePixels)

            # To calculate the margins we need to know some hardware info
            # Printer has special "support studs" that
            # let 19 & 24mm tapes go to the bottom (if supported)
            # but 12mm based casettes are raised so they are centered to the printhead.
            # Smaller tapes than 12mm are in 12mm casettes are centered
            # in the cartridge and in turn also centered to the printhead
            # Which gives us the advantage that we can
            # just calculate the top and bottom margin

            # Calculate the top margin
            topMargin = round(((self.printHeadSizePixels - activeTapePixels) / 2), 0)

            # Bottom margin is equal due to centering of the tape
            bottomMargin = topMargin

            # Make sure the total is the exact amount of pixels of the printhead
            # Aka compensate for margin rounding/division errors
            activeTapePixels = self.printHeadSizePixels - (topMargin + bottomMargin)

            # Return active pixels / margins set
            return (int(activeTapePixels), int(topMargin), int(bottomMargin))
        else:
            # Tape size not supported
            raise ValueError(
                f"Unsupported tape size {tapeSizeMM}mm. "
                f"Supported sizes: {self.supportedTapeSizes}mm"
            )
