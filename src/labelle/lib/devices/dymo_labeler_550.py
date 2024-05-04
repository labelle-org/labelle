from __future__ import annotations

import logging

from labelle.lib.devices.dymo_labeler_550_commands import Command, DymoLabeler550Command

LOG = logging.getLogger(__name__)


class CommandBatch:
    def __init__(
        self,
        title: str | None = None,
        commands: list[Command] | None = None,
    ) -> None:
        self.title = title
        self.commands: list[Command] = commands or []

    @property
    def descriptions(self) -> tuple[str, ...]:
        return tuple(command.description for command in self.commands)

    @property
    def payloads(self) -> tuple[bytes, ...]:
        return tuple(command.payload for command in self.commands)

    @property
    def payload(self) -> bytes:
        return b"".join(self.payloads)


class LabelData:
    def __init__(self, width: int, height: int, data: bytes) -> None:
        assert len(data) == width * height
        self.width = width
        self.height = height
        self.data = data


class DymoLabeler550CommandBatch(CommandBatch):
    def __init__(
        self,
        title: str | None = None,
        commands: list[Command] | None = None,
    ) -> None:
        super().__init__(title, commands)

    @staticmethod
    def _print_job_header(job_id: int = 0) -> DymoLabeler550CommandBatch:
        """Construct Print Job Header.

        The Print Job Header is the beginning of a print job structure.
        It is mandatory to have <ESC s> to let the printer know the start of the print
        job. The table below shows the mandatory command for the header section along
        with optional commands that can be placed in this section.

        +-------------------------------------------------------+
        |                   Mandatory Commands                  |
        +------------------------------------------+------------+
        | Start of Print Job                       | <ESC s>    |
        +------------------------------------------+------------+
        |                   Optional Commands                   |
        +------------------------------------------+------------+
        | Set Maximum Label Length                 | <ESC L>    |
        +------------------------------------------+------------+
        | Select Text Output Mode or               | <ESC h> or |
        | Select Graphics Output Mode              | <ESC i>    |
        +------------------------------------------+------------+
        | Select Energy Setting                    | <ESC C>    |
        +------------------------------------------+------------+
        | Set Output Tray                          |            |
        * (will be supported by LW550 Twin Turbo)  | <ESC C>    |
        +------------------------------------------+------------+
        | Select Content Type                      | <ESC T>    |
        +------------------------------------------+------------+

        Original documentation notes:
        - Missing documentation for Select Energy Setting command
        - Documentation for Set Maximum Label Length command is partial
        """
        return DymoLabeler550CommandBatch(
            "Print Job Header",
            commands=[
                DymoLabeler550Command.start_of_print_job(job_id),
                DymoLabeler550Command.select_graphics_output_mode(),
            ],
        )

    @staticmethod
    def _print_label(
        width: int,
        height: int,
        print_data: bytes,
        label_index: int = 0,
        feed_to_cut=True,
    ) -> DymoLabeler550CommandBatch:
        if feed_to_cut:
            feed_command = DymoLabeler550Command.feed_to_tear_position
        else:
            feed_command = DymoLabeler550Command.feed_to_print_head
        return DymoLabeler550CommandBatch(
            f"Print Label #{label_index}",
            commands=[
                DymoLabeler550Command.set_label_index(label_index),
                DymoLabeler550Command.label_print_data(width, height, print_data),
                feed_command(),
            ],
        )

    @staticmethod
    def label_print_job(
        labels: list[LabelData],
        job_id: int = 0,
    ) -> DymoLabeler550CommandBatch:
        label_batches = []
        for label_id, label in enumerate(labels):
            is_last_label = label_id == len(labels) - 1
            batch = DymoLabeler550CommandBatch._print_label(
                width=label.width,
                height=label.height,
                print_data=label.data,
                label_index=label_id,
                feed_to_cut=is_last_label,
            )
            label_batches.append(batch)

        batches = [
            DymoLabeler550CommandBatch._print_job_header(job_id),
            *label_batches,
            DymoLabeler550CommandBatch(
                title="End of Print Job",
                commands=[DymoLabeler550Command.end_of_print_job()],
            ),
        ]
        return DymoLabeler550CommandBatch(
            title=f"Label Print Job #{job_id}",
            commands=[command for batch in batches for command in batch.commands],
        )
