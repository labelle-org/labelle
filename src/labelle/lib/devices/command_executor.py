from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, BinaryIO, Callable

from retry.api import retry_call  # type: ignore[import-untyped]

LOG = logging.getLogger(__name__)


class Command:
    def __init__(self, description: str, payload: bytes) -> None:
        self.description: str = description
        self.payload: bytes = payload


class Response(ABC):
    retry_exceptions: tuple[type[Exception]] | None = None

    def __init__(self, retry_exceptions: tuple[type[Exception]] | None = None) -> None:
        self.retry_exceptions = retry_exceptions

    @abstractmethod
    def parse(self, response: bytes) -> Response:
        raise NotImplementedError()


class CommandExecutor:
    """Reference: https://download.dymo.com/dymo/user-guides/LabelWriter/LW550Series/LW%20550%20Technical%20Reference.pdf."""

    def __init__(self, devin: BinaryIO | None = None, devout: BinaryIO | None = None):
        self._devin: BinaryIO | None = devin
        self._devout: BinaryIO | None = devout

    def _send_command(self, command: Command) -> None:
        LOG.debug(f"Sending command: {command.description}")
        print(
            f"Sending payload: {bytes.hex(command.payload).upper()} "
            f"with {command.description}"
        )
        if self._devout is not None:
            self._devout.write(command.payload)
            self._devout.flush()

    def _receive_response(self, n: int = -1) -> bytes:
        response = b""
        if self._devin is not None:
            response = self._devin.read(n)
        response_payload = bytes(response)  # convert from array.array to bytes
        payload_str = " ".join([f"{x:02x}" for x in response_payload])
        LOG.debug(f"Read {len(response_payload)} bytes: {payload_str}")
        return response_payload

    def _execute(
        self, command: Command, response: Response | None = None
    ) -> Response | None:
        self._send_command(command)
        if response is not None:
            resp = response.parse(self._receive_response())
            LOG.debug(f"Response: {response}")
            return resp
        return None

    def execute(self, command: Command, response: Response | None = None) -> Any:
        if exceptions := response and response.retry_exceptions:
            return retry_call(
                self._execute,
                # fargs=fargs,
                # fkwargs=*fkwargs,
                fkwargs={"command": command, "response": response},
                exceptions=exceptions,
                tries=10,
                delay=0.5,
            )
        else:
            return self._execute(command=command, response=response)

    @staticmethod
    def command(
        f: Callable[..., Command], response: Response | None = None
    ) -> Callable[..., Response | None]:
        print(f">>>>>>>>>>>> wrapping f={f}")

        @wraps(f)
        def wrapper(self, *args, **kwargs):
            cmd: Command = f(*args, **kwargs)
            print(f">>>>>>>>>>>> cmd={cmd}, args {args}, kwargs {kwargs}, self {self}")
            return self.execute(cmd, response=response)

        return wrapper
