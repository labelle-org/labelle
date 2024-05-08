import sys

import pytest
from typer.testing import CliRunner

from labelle.cli.cli import main

runner = CliRunner()


def test_text_hint(monkeypatch):
    # This is NOT the recommended way of testing Typer applications.
    # We are doing it this way because we added additional error handling
    # in main() which we need to test.
    with monkeypatch.context() as m:
        m.setattr(sys, "argv", ["labelle", "hello world"])
        with runner.isolation(input=None, env=None, color=False) as outstreams:
            with pytest.raises(SystemExit):
                main()
            sys.stdout.flush()
            stdout = outstreams[0].getvalue()
    assert (
        b"""No such command 'hello world'. Did you mean --text 'hello world' ?"""
        in stdout
    )
