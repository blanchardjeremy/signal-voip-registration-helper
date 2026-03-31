"""
Pre-built Signal launcher icon variants (launcher_icons/*.icns).

IDs and labels are used by the wizard and create_signal_launcher.py.
Tint RGB values are only for dev/build_launcher_icons.py (Pillow); not a runtime dependency.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

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
