import pytest

from labelle.lib.devices.dymo_labeler_550_commands import (
    Command,
    DymoLabeler550Command,
    DymoLabeler550SpeedMode,
)


def verify_command(command: Command, description: str, payload: str):
    assert bytes.hex(command.payload).upper() == payload.replace(" ", "")
    assert command.description == description


def test_start_of_print_job():
    verify_command(
        DymoLabeler550Command().start_of_print_job(),
        "Start of Print Job #0",
        "1B 73 00000000",
    )
    verify_command(
        DymoLabeler550Command().start_of_print_job(job_id=42),
        "Start of Print Job #42",
        "1B 73 0000002A",
    )


def test_set_maximum_label_length():
    verify_command(
        DymoLabeler550Command().set_maximum_label_length(),
        "Set Maximum Label Length",
        "1B 4C",
    )


def test_select_text_output_mode():
    verify_command(
        DymoLabeler550Command().select_text_output_mode(),
        "Select Text Output Mode",
        "1B 68",
    )


def test_select_graphics_output_mode():
    verify_command(
        DymoLabeler550Command().select_graphics_output_mode(),
        "Select Graphics Output Mode",
        "1B 69",
    )


def test_content_type():
    verify_command(
        DymoLabeler550Command().content_type(),
        "Content Type (Speed Mode NORMAL_SPEED)",
        "1B 54 10",
    )
    verify_command(
        DymoLabeler550Command().content_type(
            speed_mode=DymoLabeler550SpeedMode.NORMAL_SPEED
        ),
        "Content Type (Speed Mode NORMAL_SPEED)",
        "1B 54 10",
    )
    verify_command(
        DymoLabeler550Command().content_type(
            speed_mode=DymoLabeler550SpeedMode.HIGH_SPEED
        ),
        "Content Type (Speed Mode HIGH_SPEED)",
        "1B 54 20",
    )


def test_set_label_index():
    verify_command(
        DymoLabeler550Command().set_label_index(), "Set Label Index #0", "1B 6E 0000"
    )
    verify_command(
        DymoLabeler550Command().set_label_index(label_index=42),
        "Set Label Index #42",
        "1B 6E 002A",
    )


def test_label_print_data():
    verify_command(
        DymoLabeler550Command().label_print_data(
            width=4,
            height=2,
            print_data=bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x00, 0x11]),
        ),
        "Label Print Data (Width 4, Height 2)",
        "1B 44 01 02 00000004 00000002 AABBCCDDEEFF0011",
    )


def test_short_form_feed():
    verify_command(
        DymoLabeler550Command().feed_to_print_head(),
        "Feed to Print Head (Short Form Feed)",
        "1B 47",
    )


def test_long_form_feed():
    verify_command(
        DymoLabeler550Command().feed_to_tear_position(),
        "Feed to Tear Position (Long Form Feed)",
        "1B 45",
    )


def test_end_of_print_job():
    verify_command(
        DymoLabeler550Command().end_of_print_job(), "End of Print Job", "1B 51"
    )


def test_set_print_density():
    verify_command(
        DymoLabeler550Command().set_print_density(),
        "Set Print Density (Duty Cycle 100)",
        "1B 43 64",
    )
    verify_command(
        DymoLabeler550Command().set_print_density(duty_cycle=0),
        "Set Print Density (Duty Cycle 0)",
        "1B 43 00",
    )
    verify_command(
        DymoLabeler550Command().set_print_density(duty_cycle=200),
        "Set Print Density (Duty Cycle 200)",
        "1B 43 C8",
    )
    with pytest.raises(AssertionError):
        DymoLabeler550Command().set_print_density(duty_cycle=300)


def test_reset_print_density_to_default():
    verify_command(
        DymoLabeler550Command().reset_print_density_to_default(),
        "Set Print Density to Default",
        "1B 65",
    )


def test_restart_print_engine():
    verify_command(
        DymoLabeler550Command().restart_print_engine(),
        "Reboot the print engine",
        "1B 40",
    )


def test_restore_print_engine_factory_settings():
    verify_command(
        DymoLabeler550Command().restore_print_engine_factory_settings(),
        "Restore all the factory settings of the printer",
        "1B 24",
    )


def test_set_label_count():
    verify_command(
        DymoLabeler550Command().set_label_count(label_count=0),
        "Set label count (Label Count 0)",
        "1B 6F 00",
    )
    verify_command(
        DymoLabeler550Command().set_label_count(label_count=200),
        "Set label count (Label Count 200)",
        "1B 6F C8",
    )
    with pytest.raises(AssertionError):
        DymoLabeler550Command().set_label_count(label_count=300)
