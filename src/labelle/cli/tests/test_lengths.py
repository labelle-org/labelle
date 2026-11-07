import math
from unittest.mock import Mock

import pytest
from PIL import Image
from typer.testing import CliRunner

from labelle.cli import cli
from labelle.lib.constants import PIXELS_PER_MM
from labelle.lib.render_engines.margins import BitmapTooBigError


@pytest.fixture
def rendered_bitmaps(monkeypatch):
    rendered = []
    monkeypatch.setattr(
        cli, "output_bitmap", lambda bitmap, output: rendered.append(bitmap)
    )
    device_manager = Mock()
    monkeypatch.setattr(cli, "get_device_manager", lambda: device_manager)
    monkeypatch.setattr(
        cli.DymoLabeler, "print", lambda self, bitmap: rendered.append(bitmap)
    )
    return rendered


@pytest.mark.parametrize(
    "length_option", ["--fixed-length", "--min-length", "--max-length"]
)
@pytest.mark.parametrize("output", ["console", "printer"])
def test_label_length_includes_margins(
    rendered_bitmaps, tmp_path, length_option, output
):
    picture = tmp_path / "label.png"
    Image.new("1", (180, 64), color=1).save(picture)
    result = CliRunner().invoke(
        cli.app,
        [
            "--output",
            output,
            "--picture",
            str(picture),
            "--margin-px",
            "14",
            length_option,
            "30",
        ],
    )

    assert result.exit_code == 0, result.output
    expected_width = (
        208 if length_option == "--max-length" else math.ceil(30 * PIXELS_PER_MM)
    )
    assert len(rendered_bitmaps) == 1
    assert rendered_bitmaps[0].width == expected_width


@pytest.mark.parametrize("output", ["console", "printer"])
def test_max_length_rejects_content_exceeding_margins(
    rendered_bitmaps, tmp_path, output
):
    picture = tmp_path / "label.png"
    payload_width = math.ceil(30 * PIXELS_PER_MM) - 2 * 14 + 1
    Image.new("1", (payload_width, 64), color=1).save(picture)

    result = CliRunner().invoke(
        cli.app,
        [
            "--output",
            output,
            "--picture",
            str(picture),
            "--margin-px",
            "14",
            "--max-length",
            "30",
        ],
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, BitmapTooBigError)
    assert not rendered_bitmaps


@pytest.mark.parametrize("fixed_length", ["0", "-1"])
def test_fixed_length_must_be_positive(fixed_length):
    result = CliRunner().invoke(
        cli.app, ["--output", "console", "--fixed-length", fixed_length, "label"]
    )

    assert result.exit_code == 2
    assert "Fixed length must be positive" in result.output
