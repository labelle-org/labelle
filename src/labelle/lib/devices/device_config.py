from __future__ import annotations

import logging
import math

LOG = logging.getLogger(__name__)


class DeviceConfig:
    """Configuration object for the capabilities of a label printer."""

    name: str
    """Name of this device"""

    device_ids: list[int]
    """List of USB Device ID's this device can identify as"""

    print_head_width_px: int
    """Size of the print head in pixels (use calibration routine to determine)"""

    print_head_active_area_width_mm: float
    """Size of the active area of the print head in millimters
        (use calibration routine to determine)"""

    supported_tape_sizes_mm: list[int]
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
        device_ids: list[int],
        print_head_width_px: int,
        print_head_active_area_width_mm: int,
        supported_tape_sizes_mm: list[int],
    ):
        """Initialize a Labeler config object."""
        self.name = name
        self.device_ids = device_ids
        self.print_head_width_px = print_head_width_px
        self.print_head_active_area_width_mm = print_head_active_area_width_mm
        self.supported_tape_sizes_mm = supported_tape_sizes_mm

    def matches_device_id(self, device_id: int) -> bool:
        """Check if the a device ID matches this config."""
        if device_id in self.device_ids:
            return True
        else:
            return False

    def get_tape_print_size_and_margins_px(
        self, tape_size_mm: int
    ) -> tuple[int, int, int]:
        """Get print margins for a specific tape size.

        :param tape_size_mm: Tape size in mm
        :return: Margins tuple in pixels
            (Active pixels on tape, Top margin pixels, bottom margin pixels)
        """
        if tape_size_mm in self.supported_tape_sizes_mm:
            # Calculate the pixels per mm for this printer
            # Example: printhead of 128 Pixels, distributed over 18 mm of active area.
            #   Makes 7.11 pixels/mm
            print_pixels_per_mm: float = (
                self.print_head_width_px / self.print_head_active_area_width_mm
            )

            # Calculate usable tape width (*2 for top and bottom)
            usable_tape_width_mm: float = tape_size_mm - (
                self.TAPE_ALIGNMENT_INACCURACY_MM * 2
            )

            # Calculate the numer of active pixels for the tape
            usable_tape_width_pixels: float = 0
            if usable_tape_width_mm >= self.print_head_active_area_width_mm:
                # Tape is larger than active area of printhead. Use all pixels
                usable_tape_width_pixels = self.print_head_width_px
            else:
                # Calculate the amount of active pixels we are able to use
                # (taking the placement inaccuracy into account)
                usable_tape_width_pixels = print_pixels_per_mm * usable_tape_width_mm

            # Round down to nearest whole number as we can't use half a pixels ;)
            usable_tape_width_pixels = math.floor(usable_tape_width_pixels)

            # To calculate the margins we need to know some hardware info
            # Printer has special "support studs" that
            # let 19 & 24mm tapes go to the bottom (if supported)
            # but 12mm based casettes are raised so they are centered to the printhead.
            # Smaller tapes than 12mm are in 12mm casettes are centered
            # in the cartridge and in turn also centered to the printhead
            # Which gives us the advantage that we can
            # just calculate the top and bottom margin

            # Calculate the top margin
            margin_top = round(
                ((self.print_head_width_px - usable_tape_width_pixels) / 2), 0
            )

            # Bottom margin is equal due to centering of the tape
            margin_bottom = margin_top

            # Make sure the total is the exact amount of pixels of the printhead
            # Aka compensate for margin rounding/division errors
            usable_tape_width_pixels = self.print_head_width_px - (
                margin_top + margin_bottom
            )

            # Return active pixels / margins set
            return (int(usable_tape_width_pixels), int(margin_top), int(margin_bottom))
        else:
            # Tape size not supported
            raise ValueError(
                f"Unsupported tape size {tape_size_mm}mm. "
                f"Supported sizes: {self.supported_tape_sizes_mm}mm"
            )
