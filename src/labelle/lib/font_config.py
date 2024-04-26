import logging
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import labelle.resources.fonts
from labelle._vendor.matplotlib import font_manager
from labelle.lib.config_file import get_config_section

logger = logging.getLogger(__name__)


class NoFontFound(ValueError):
    def __init__(self, name):
        msg = f"No font named {name} found"
        super().__init__(msg)


class NoStyleFound(ValueError):
    def __init__(self, style):
        msg = f"No style named {style} found"
        super().__init__(msg)


_DEFAULT_FONTS_DIR = Path(labelle.resources.fonts.__file__).parent
_DEFAULT_STYLE = "regular"
_DEFAULT_STYLES_TO_FONT_PATH: Dict[str, Path] = {
    "regular": _DEFAULT_FONTS_DIR / "Carlito-Regular.ttf",
    "bold": _DEFAULT_FONTS_DIR / "Carlito-Bold.ttf",
    "italic": _DEFAULT_FONTS_DIR / "Carlito-Italic.ttf",
    "narrow": _DEFAULT_FONTS_DIR / "Carlito-BoldItalic.ttf",
}


class FontStyle(str, Enum):
    REGULAR = "regular"
    BOLD = "bold"
    ITALIC = "italic"
    NARROW = "narrow"


DefaultFontStyle = FontStyle(_DEFAULT_STYLE)


def _get_styles_to_font_path_lookup() -> Dict[str, Path]:
    """Get a lookup table for styles to font paths.

    The lookup table is read from the config file, if available.
    """
    styles_to_font_path = _DEFAULT_STYLES_TO_FONT_PATH.copy()
    fonts_config = get_config_section("FONTS")
    if fonts_config is not None:
        for style_from_config, filename in fonts_config.items():
            styles_to_font_path[style_from_config] = Path(filename)
    return styles_to_font_path


def get_font_path(
    font: Optional[str] = None, style: Optional[str] = _DEFAULT_STYLE
) -> Path:
    """Get the path to a font.

    The `font` argument can be either a font name or a path to a font file.
    If `font` is not provided, the default font is used. In that case, the `style`
    argument can be used to specify the style of the default font.
    """
    if font is not None:
        if Path(font).is_file():
            path = Path(font)
        else:
            path = _path_from_name(name=font)
    else:
        styles_to_font_path = _get_styles_to_font_path_lookup()
        if style in styles_to_font_path:
            path = styles_to_font_path[style]
        else:
            logger.debug(f"Style '{style}' unrecognized. Known: {styles_to_font_path}")
            raise NoStyleFound(style)

    # Double-check that the file exists
    if not Path(path).is_file():
        logger.error(f"Font file not found: {path}")
        raise NoFontFound(font)
    return path


def _path_from_name(name: str) -> Path:
    """Get the path to a font from its name.

    The name should be the name of the font file, without the extension.
    It is case-insensitive.
    """
    available_fonts = get_available_fonts()
    matching_fonts = [f for f in available_fonts if name.lower() == f.stem.lower()]
    if len(matching_fonts) == 0:
        raise NoFontFound(name)
    return matching_fonts[0]


def get_available_fonts() -> List[Path]:
    """Get a list of available font files."""
    fonts = [f for f in _DEFAULT_FONTS_DIR.iterdir() if f.suffix == ".ttf"]
    fonts.extend(Path(f) for f in font_manager.findSystemFonts())
    return sorted(fonts, key=lambda f: f.stem.lower())
