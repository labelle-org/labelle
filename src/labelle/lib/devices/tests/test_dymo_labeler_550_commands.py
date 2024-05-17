import io
import logging

import pytest

from labelle.lib.devices.dymo_labeler_550_commands import (
    DymoLabeler550Command,
    DymoLabeler550SpeedMode,
)


@pytest.fixture
def debug_caplog(caplog):
    with caplog.at_level(logging.DEBUG):
        yield caplog


@pytest.fixture
def commands():
    cmds = DymoLabeler550Command(devout=io.BytesIO())
    try:
        yield cmds
    finally:
        if cmds._devout is not None:
            cmds._devout.close()


class Tester:
    def __init__(self, debug_caplog, commands):
        self.debug_caplog = debug_caplog
        self.commands = commands

    def verify(self, expected_description: str, expected_payload: str):
        assert expected_description in self.debug_caplog.text
        self.debug_caplog.clear()  # for following checks in the same test function
        actual_payload = bytes.hex(self.commands._devout.getvalue()).upper()
        assert actual_payload == expected_payload.replace(" ", "")


@pytest.fixture
def tester(debug_caplog, commands):
    return Tester(debug_caplog, commands)


def test_start_of_print_job(tester):
    tester.commands.start_of_print_job()
    tester.verify(
        "Sending command: Start of Print Job #0",
        "1B 73 00000000",
    )


def test_start_of_print_job_with_params(tester):
    tester.commands.start_of_print_job(job_id=42)
    tester.verify(
        "Sending command: Start of Print Job #42",
        "1B 73 2A000000",
    )


def test_set_maximum_label_length(tester):
    tester.commands.set_maximum_label_length()
    tester.verify(
        "Set Maximum Label Length",
        "1B 4C",
    )


def test_select_text_output_mode(tester):
    tester.commands.select_text_output_mode()
    tester.verify(
        "Select Text Output Mode",
        "1B 68",
    )


def test_select_graphics_output_mode(tester):
    tester.commands.select_graphics_output_mode()
    tester.verify(
        "Select Graphics Output Mode",
        "1B 69",
    )


def test_content_type(tester):
    tester.commands.content_type()
    tester.verify(
        "Content Type (Speed Mode NORMAL_SPEED)",
        "1B 54 10",
    )


def test_content_type_normal_speed(tester):
    tester.commands.content_type(speed_mode=DymoLabeler550SpeedMode.NORMAL_SPEED)
    tester.verify(
        "Content Type (Speed Mode NORMAL_SPEED)",
        "1B 54 10",
    )


def test_content_type_high_speed(tester):
    tester.commands.content_type(speed_mode=DymoLabeler550SpeedMode.HIGH_SPEED)
    tester.verify(
        "Content Type (Speed Mode HIGH_SPEED)",
        "1B 54 20",
    )


def test_set_label_index(tester):
    tester.commands.set_label_index()
    tester.verify("Set Label Index #0", "1B 6E 0000")


def test_set_label_index_with_params(tester):
    tester.commands.set_label_index(label_index=42)
    tester.verify(
        "Set Label Index #42",
        "1B 6E 2A00",
    )


def test_label_print_data(tester):
    tester.commands.label_print_data(
        width=4,
        height=2,
        print_data=bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x00, 0x11]),
    )
    tester.verify(
        "Label Print Data (Width 4, Height 2)",
        "1B 44 01 02 00000004 00000002 AABBCCDDEEFF0011",
    )


def test_short_form_feed(tester):
    tester.commands.feed_to_print_head()
    tester.verify(
        "Feed to Print Head (Short Form Feed)",
        "1B 47",
    )


def test_long_form_feed(tester):
    tester.commands.feed_to_tear_position()
    tester.verify(
        "Feed to Tear Position (Long Form Feed)",
        "1B 45",
    )


def test_end_of_print_job(tester):
    tester.commands.end_of_print_job()
    tester.verify("End of Print Job", "1B 51")


def test_set_print_density(tester):
    tester.commands.set_print_density()
    tester.verify("Set Print Density (Duty Cycle 100)", "1B 43 64")


def test_set_print_density_duty_cycle_0(tester):
    tester.commands.set_print_density(duty_cycle=0)
    tester.verify(
        "Set Print Density (Duty Cycle 0)",
        "1B 43 00",
    )


def test_set_print_density_duty_cycle_200(tester):
    tester.commands.set_print_density(duty_cycle=200)
    tester.verify(
        "Set Print Density (Duty Cycle 200)",
        "1B 43 C8",
    )
    with pytest.raises(AssertionError):
        tester.commands.set_print_density(duty_cycle=300)


def test_reset_print_density_to_default(tester):
    tester.commands.reset_print_density_to_default()
    tester.verify(
        "Set Print Density to Default",
        "1B 65",
    )


def test_restart_print_engine(tester):
    tester.commands.restart_print_engine()
    tester.verify(
        "Restart Print Engine",
        "1B 2A",
    )


def test_restore_print_engine_factory_settings(tester):
    tester.commands.restore_print_engine_factory_settings()
    tester.verify(
        "Restore all the factory settings of the printer",
        "1B 24",
    )


def test_set_label_count_zero(tester):
    tester.commands.set_label_count(label_count=0)
    tester.verify(
        "Set label count (Label Count 0)",
        "1B 6F 00",
    )


def test_set_label_count_200(tester):
    tester.commands.set_label_count(label_count=200)
    tester.verify(
        "Set label count (Label Count 200)",
        "1B 6F C8",
    )
    with pytest.raises(AssertionError):
        tester.commands.set_label_count(label_count=300)
