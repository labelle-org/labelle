from typing import NamedTuple


class RenderContext(NamedTuple):
    height_px: int
    preview_show_margins: bool = True
    background_color: str = "white"
    foreground_color: str = "black"
