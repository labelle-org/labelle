from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from labelle.cli.cli import app
from labelle.lib.render_engines import TextRenderEngine


@pytest.mark.parametrize(
    "batch_input",
    [
        "",
        "\n",
        "LABELLE-LABEL-SPEC-VERSION\n",
        "LABELLE-LABEL-SPEC-VERSION:2\n",
        "invalid\n",
    ],
)
def test_invalid_batch_header(batch_input):
    result = CliRunner().invoke(
        app, ["--batch", "--output", "console"], input=batch_input
    )
    assert result.exit_code == 2
    assert "Batch doesn't begin with LABELLE-LABEL-SPEC-VERSION:1" in result.output
    assert not isinstance(result.exception, (IndexError, ValueError))


@pytest.mark.parametrize("line", ["", "TEXT without colon"])
def test_invalid_batch_body_line(line):
    result = CliRunner().invoke(
        app,
        ["--batch", "--output", "console"],
        input=f"LABELLE-LABEL-SPEC-VERSION:1\nTEXT:valid\n{line}\n",
    )
    assert result.exit_code == 2
    assert "Invalid batch line 3: expected COMMAND:value" in result.output
    assert not isinstance(result.exception, (IndexError, ValueError))


def test_valid_batch_preserves_colons_and_multiline_text():
    with patch(
        "labelle.cli.cli.TextRenderEngine", wraps=TextRenderEngine
    ) as render_text:
        result = CliRunner().invoke(
            app,
            ["--batch", "--output", "console"],
            input="LABELLE-LABEL-SPEC-VERSION:1\nTEXT:hello:world\nNEWLINE:again\n",
        )
    assert result.exit_code == 0, result.output
    render_text.assert_called_once()
    assert render_text.call_args.kwargs["text_lines"] == ["hello:world", "again"]
