from labelle.lib.devices.dymo_labeler_550 import (
    DymoLabeler550CommandBatch,
    LabelData,
)


def verify_command_batch(
    command_batch: DymoLabeler550CommandBatch,
    expected_title: str,
    expected_commands: tuple[tuple[str, str], ...],
):
    assert command_batch.title == expected_title
    descriptions, payloads = zip(*expected_commands)
    assert command_batch.descriptions == descriptions
    assert [bytes.hex(payload).upper() for payload in command_batch.payloads] == [
        payload.replace(" ", "") for payload in payloads
    ]


def test_print_job_header():
    command_batch = DymoLabeler550CommandBatch()._print_job_header()
    verify_command_batch(
        command_batch,
        expected_title="Print Job Header",
        expected_commands=(
            ("Start of Print Job #0", "1B 73 00000000"),
            ("Select Graphics Output Mode", "1B 69"),
        ),
    )
    assert command_batch.payload == bytes.fromhex("1B7300000000 1B69")


def test_print_label():
    command_batch = DymoLabeler550CommandBatch()._print_label(
        width=2, height=3, print_data=b"123456"
    )
    verify_command_batch(
        command_batch,
        expected_title="Print Label #0",
        expected_commands=(
            ("Set Label Index #0", "1B 6E 0000"),
            (
                "Label Print Data (Width 2, Height 3)",
                "1B 44 01 02 00000002 00000003 313233343536",
            ),
            ("Feed to Tear Position (Long Form Feed)", "1B 45"),
        ),
    )


def test_label_print_job_single():
    labels = [
        LabelData(width=2, height=3, data=b"123456"),
    ]
    command_batch = DymoLabeler550CommandBatch().label_print_job(labels)
    verify_command_batch(
        command_batch,
        expected_title="Label Print Job #0",
        expected_commands=(
            ("Start of Print Job #0", "1B 73 00000000"),
            ("Select Graphics Output Mode", "1B 69"),
            ("Set Label Index #0", "1B 6E 0000"),
            (
                "Label Print Data (Width 2, Height 3)",
                "1B 44 01 02 00000002 00000003 313233343536",
            ),
            ("Feed to Tear Position (Long Form Feed)", "1B 45"),
            ("End of Print Job", "1B 51"),
        ),
    )


def test_label_print_job_multiple():
    labels = [
        LabelData(width=2, height=3, data=b"123456"),
        LabelData(width=4, height=4, data=b"7890ABCDEF012345"),
    ]
    command_batch = DymoLabeler550CommandBatch().label_print_job(labels)
    verify_command_batch(
        command_batch,
        expected_title="Label Print Job #0",
        expected_commands=(
            ("Start of Print Job #0", "1B 73 00000000"),
            ("Select Graphics Output Mode", "1B 69"),
            ("Set Label Index #0", "1B 6E 0000"),
            (
                "Label Print Data (Width 2, Height 3)",
                "1B 44 01 02 00000002 00000003 313233343536",
            ),
            ("Feed to Print Head (Short Form Feed)", "1B 47"),
            ("Set Label Index #1", "1B 6E 0001"),
            (
                "Label Print Data (Width 4, Height 4)",
                "1B 44 01 02 00000004 00000004 37383930414243444546303132333435",
            ),
            ("Feed to Tear Position (Long Form Feed)", "1B 45"),
            ("End of Print Job", "1B 51"),
        ),
    )


def test_label_print_job_none():
    labels: list[LabelData] = []
    command_batch = DymoLabeler550CommandBatch().label_print_job(labels)
    verify_command_batch(
        command_batch,
        expected_title="Label Print Job #0",
        expected_commands=(
            ("Start of Print Job #0", "1B 73 00000000"),
            ("Select Graphics Output Mode", "1B 69"),
            ("End of Print Job", "1B 51"),
        ),
    )
