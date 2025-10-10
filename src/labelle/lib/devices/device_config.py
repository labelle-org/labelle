from __future__ import annotations

import logging
from dataclasses import dataclass

LOG = logging.getLogger(__name__)


@dataclass
class DeviceConfig:
    """Configuration object for the capabilities of a label printer."""

    name: str
    """Name of this device"""

    device_ids: list[int]
    """List of USB Device ID's this device can identify as"""

    print_head_px: int
    """Size of the print head in pixels (use calibration routine to determine)"""

    print_head_mm: float
    """Size of the active area of the print head in millimters
        (use calibration routine to determine)"""

    supported_tape_sizes_mm: list[int]
    """List of supported tape sizes in mm"""

    tape_alignment_inaccuracy_mm: float = 1.0
    """The inaccuracy of the tape position relative to the printhead

    Inaccuracy of the tape position is mostly caused by
    the tape moving slightly from side to side in the cartridge.
    Improper cartrigde placemement is also an factor,
    but negligible due to a physical spring in the lid.
    """

    distance_between_print_head_and_cutter_px: int = 57
    """Amount of unprintable tape remaining in the machine after cutting with knife."""

    def matches_device_id(self, device_id: int) -> bool:
        """Check if the a device ID matches this config."""
        return device_id in self.device_ids
