from __future__ import annotations

import logging
import struct
from enum import Enum

from labelle.lib.constants import ESC

LOG = logging.getLogger(__name__)


class Command:
    def __init__(self, description: str, payload: bytes) -> None:
        self.description: str = description
        self.payload: bytes = payload


class DymoLabeler550SpeedMode(Enum):
    NORMAL_SPEED = 0x10
    HIGH_SPEED = 0x20


class DymoLabeler550Command:
    """Reference: https://download.dymo.com/dymo/user-guides/LabelWriter/LW550Series/LW%20550%20Technical%20Reference.pdf."""

    @staticmethod
    def start_of_print_job(job_id: int = 0) -> Command:
        """ESC s Start of Print Job
        1B 73
        Indicates a new print job. A unique job ID is passed along with this command.
        """  # noqa: D205
        return Command(
            f"Start of Print Job #{job_id}",
            struct.pack("<BBI", ESC, ord("s"), job_id),
        )

    @staticmethod
    def set_maximum_label_length() -> Command:
        """ESC L Set Maximum Label Length
        1B 4C
        Sets the print engine mode between normal label stock and continuous label stock. Normal label stock is
        the default mode for the print engine.
        """  # noqa: D205, E501
        return Command("Set Maximum Label Length", struct.pack("<BB", ESC, ord("L")))

    @staticmethod
    def select_text_output_mode() -> Command:
        """ESC h Select Text Output Mode
        1B 68
        Tells the print engine that the label shall be printed with the print settings which are ideal for text. Text
        mode is the default printer setting.
        """  # noqa: D205, E501
        return Command("Select Text Output Mode", struct.pack("<BB", ESC, ord("h")))

    @staticmethod
    def select_graphics_output_mode() -> Command:
        """ESC i Select Graphics Output Mode
        1B 69
        Tells the print engine that the label shall be printed with the print settings which are ideal for graphics
        and barcodes. The print speed might be reduced in this mode.
        """  # noqa: D205, E501
        return Command("Select Graphics Output Mode", struct.pack("<BB", ESC, ord("i")))

    @staticmethod
    def content_type(
        speed_mode: DymoLabeler550SpeedMode = DymoLabeler550SpeedMode.NORMAL_SPEED,
    ) -> Command:
        """ESC T Content Type
        1B 54
        Byte
        Note: there seem to be a typo in the reference document,
              the correct command is 1B 54, not 1B 74.
        """  # noqa: D205
        return Command(
            f"Content Type (Speed Mode {speed_mode.name})",
            struct.pack("<BBB", ESC, ord("T"), speed_mode.value),
        )

    @staticmethod
    def set_label_index(label_index: int = 0) -> Command:
        """ESC n Set Label Index
        1B 6E
        Sets the label index. The same label index is returned in the print status providing the host the possibility
        to track which label is being printed. Default value is 0
        """  # noqa: D205, D400, E501
        return Command(
            f"Set Label Index #{label_index}",
            struct.pack("<BBH", ESC, ord("n"), label_index),
        )

    @staticmethod
    def label_print_data(width: int, height: int, print_data: bytes) -> Command:
        """ESC D Start of Label Print Data & Label Print Data
        1B 44
        Indicates the start of the label print data and notifies the print engine about the label's height and
        width. The height is defined in dots while the width specifies the number of lines. The width does not
        include the leader and trailer.
        """  # noqa: D205, E501
        bpp = 1
        alignment = 2
        print_data_len = len(print_data)
        assert print_data_len == width * height
        payload = (
            struct.pack(
                ">BBBBII",
                ESC,
                ord("D"),
                bpp,
                alignment,
                width,
                height,
            )
            + print_data
        )
        return Command(f"Label Print Data (Width {width}, Height {height})", payload)

    @staticmethod
    def feed_to_print_head() -> Command:
        """ESC G Feed to Print Head (Short Form Feed)
        1B 47
        Feeds the next label into print position. The most recently printed label might still be partially inside the
        printer and cannot be torn off. This command is meant to be used between labels on a multiple label
        print job.
        """  # noqa: D205, E501
        return Command(
            "Feed to Print Head (Short Form Feed)", struct.pack("<BB", ESC, ord("G"))
        )

    @staticmethod
    def feed_to_tear_position() -> Command:
        """ESC E Feed to Tear Position (Long Form Feed)
        1B 45
        Advances the most recently printed label to a position where it can be torn off by the automatic cutter.
        This positioning places the next label beyond the starting print position. Reverse-feed will be
        automatically invoked when printing the next label.
        """  # noqa: D205, E501
        return Command(
            "Feed to Tear Position (Long Form Feed)",
            struct.pack("<BB", ESC, ord("E")),
        )

    @staticmethod
    def end_of_print_job() -> Command:
        """ESC Q End of Print Job
        1B 51
        Indicates the end of a print job. Upon reception of this command the print engine will release the
        connection and start accepting other print jobs.
        """  # noqa: D205, E501
        return Command("End of Print Job", struct.pack("<BB", ESC, ord("Q")))

    @staticmethod
    def set_print_density(duty_cycle: int = 100) -> Command:
        """ESC C Set Print Density
        1B 43
        Sets the strobe time of the printer to a given percentage of its standard duty cycle. A lower value results
        in lighter printouts while a higher value leads to darker printouts. Default value is 100. Duty range is 0-
        200%.
        """  # noqa: D205, E501
        assert 0 <= duty_cycle <= 200
        return Command(
            f"Set Print Density (Duty Cycle {duty_cycle})",
            struct.pack("<BBB", ESC, ord("C"), duty_cycle),
        )

    @staticmethod
    def reset_print_density_to_default() -> Command:
        """ESC e Reset Print Density to Default
        1B 65
        Resets the print density to default value of 100%.
        """  # noqa: D205
        return Command(
            "Set Print Density to Default",
            struct.pack("<BB", ESC, ord("e")),
        )

    @staticmethod
    def restart_print_engine() -> Command:
        """ESC * Restart Print Engine
        1B 2A
        Reboots the print engine.

        Note: there seem to be a typo in the reference document,
        which says ESC @ (0x1B40)
        """  # noqa: D205
        return Command(
            "Reboot the print engine",
            struct.pack("<BB", ESC, ord("*")),
        )

    @staticmethod
    def restore_print_engine_factory_settings() -> Command:
        """ESC * Restore Print Engine Factory Settings
        1B 24
        Restores all the factory settings of the printer.
        Note: there seem to be a typo in the reference document,
              the correct command is ESC $, not ESC 24.
        """  # noqa: D205
        return Command(
            "Restore all the factory settings of the printer",
            struct.pack("<BB", ESC, ord("$")),
        )

    @staticmethod
    def set_label_count(label_count: int) -> Command:
        """ESC o Set Label Count
        Sets label count.
        """  # noqa: D205
        assert 0 <= label_count <= 255
        return Command(
            f"Set label count (Label Count {label_count})",
            struct.pack("<BBB", ESC, ord("o"), label_count),
        )
