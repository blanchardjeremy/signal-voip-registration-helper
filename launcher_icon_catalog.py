"""
Pre-built Signal launcher icon variants (launcher_icons/*.icns).

IDs and labels are used by the wizard and create_signal_launcher.py.
Tint RGB values are only for dev/build_launcher_icons.py (Pillow); not a runtime dependency.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional, Tuple

# Approximate Signal brand blue for “original” swatch (tint table uses None for that variant)
_ORIGINAL_ICON_RGB: Tuple[int, int, int] = (59, 140, 188)

# (id, user-visible label) — order matches the numbered picker (1..12)
LAUNCHER_ICON_CHOICES: List[Tuple[str, str]] = [
    ("original", "Original (Signal blue)"),
    ("rose", "Rose"),
    ("coral", "Coral"),
    ("amber", "Amber"),
    ("lime", "Lime"),
    ("forest", "Forest"),
    ("teal", "Teal"),
    ("cyan", "Cyan"),
    ("sky", "Sky"),
    ("indigo", "Indigo"),
    ("violet", "Violet"),
    ("magenta", "Magenta"),
]

# None => copy Signal’s icon.icns verbatim; otherwise RGB tint for dev build script
ICON_BUILD_TINTS: Dict[str, Optional[Tuple[int, int, int]]] = {
    "original": None,
    "rose": (220, 72, 95),
    "coral": (235, 110, 70),
    "amber": (230, 165, 40),
    "lime": (120, 195, 55),
    "forest": (45, 140, 75),
    "teal": (35, 155, 155),
    "cyan": (45, 175, 215),
    "sky": (70, 130, 230),
    "indigo": (95, 85, 200),
    "violet": (155, 85, 210),
    "magenta": (210, 70, 165),
}


def default_launcher_icon_id() -> str:
    return LAUNCHER_ICON_CHOICES[0][0]


def launcher_icon_label(icon_id: str) -> str:
    for sid, label in LAUNCHER_ICON_CHOICES:
        if sid == icon_id:
            return label
    return icon_id


def is_valid_launcher_icon_id(icon_id: str) -> bool:
    return any(sid == icon_id for sid, _ in LAUNCHER_ICON_CHOICES)


def icon_preview_rgb(icon_id: str) -> Tuple[int, int, int]:
    """RGB used for CLI swatches (matches ICON_BUILD_TINTS where present)."""
    if icon_id == "original":
        return _ORIGINAL_ICON_RGB
    rgb = ICON_BUILD_TINTS.get(icon_id)
    if rgb is not None:
        return rgb
    return (128, 128, 128)


def _terminal_colors_enabled() -> bool:
    if os.environ.get("NO_COLOR", "").strip():
        return False
    return sys.stdout.isatty()


def launcher_icon_swatch(icon_id: str, width: int = 4) -> str:
    """
    Colored block using ANSI truecolor (24-bit) background.
    Falls back to plain Unicode blocks when colors are disabled.
    """
    if not _terminal_colors_enabled():
        return "■" * min(width, 4)
    r, g, b = icon_preview_rgb(icon_id)
    spaces = " " * width
    return f"\033[48;2;{r};{g};{b}m{spaces}\033[0m"


def format_launcher_icon_menu_line(index: int, icon_id: str, label: str) -> str:
    """One numbered line for picker UIs, e.g. '  1. [swatch] Original (Signal blue)'."""
    return f"  {index:2}. {launcher_icon_swatch(icon_id)}  {label}"
