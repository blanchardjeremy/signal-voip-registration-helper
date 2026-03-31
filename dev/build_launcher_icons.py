#!/usr/bin/env python3
"""
One-time / maintainer script: build tinted .icns files for Signal profile launchers.

Requires: macOS (sips, iconutil), Pillow, Signal.app at default path for source icon.

  pip install Pillow
  python3 dev/build_launcher_icons.py

Outputs launcher_icons/<id>.icns — commit those files; runtime has no Pillow dependency.
Tint definitions live in launcher_icon_catalog.py (ICON_BUILD_TINTS).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "launcher_icons"
SOURCE_ICNS = Path("/Applications/Signal.app/Contents/Resources/icon.icns")

# Ensure repo root on path for launcher_icon_catalog
sys.path.insert(0, str(REPO_ROOT))
from launcher_icon_catalog import ICON_BUILD_TINTS, LAUNCHER_ICON_CHOICES  # noqa: E402


def _need_pillow():
    try:
        from PIL import Image, ImageOps  # noqa: F401
    except ImportError:
        print("Install Pillow to build launcher icons: pip install Pillow", file=sys.stderr)
        sys.exit(1)


def _load_base_rgba(source: Path):
    from PIL import Image

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        r = subprocess.run(
            ["sips", "-s", "format", "png", str(source), "--out", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(r.stderr or r.stdout, file=sys.stderr)
            raise RuntimeError("sips could not convert icon.icns to PNG")
        im = Image.open(tmp_path).convert("RGBA")
    finally:
        tmp_path.unlink(missing_ok=True)

    w, h = im.size
    m = max(w, h)
    if m < 512 or m != 1024:
        im = im.resize((1024, 1024), Image.Resampling.LANCZOS)
    return im


def _tint_rgba(im, rgb: tuple[int, int, int]):
    from PIL import ImageOps

    r, g, b = rgb
    gray = im.convert("L")
    dark = (max(0, int(r * 0.2)), max(0, int(g * 0.2)), max(0, int(b * 0.2)))
    light = (min(255, r), min(255, g), min(255, b))
    rgb_img = ImageOps.colorize(gray, dark, light).convert("RGBA")
    rgb_img.putalpha(im.split()[3])
    return rgb_img


def _png_to_icns(png_path: Path, icns_path: Path) -> None:
    specs = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]
    with tempfile.TemporaryDirectory() as td:
        iconset = Path(td) / "icon.iconset"
        iconset.mkdir()
        for size, name in specs:
            subprocess.run(
                ["sips", "-z", str(size), str(size), str(png_path), "--out", str(iconset / name)],
                check=True,
                capture_output=True,
            )
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(icns_path)],
            check=True,
            capture_output=True,
        )


def main() -> None:
    _need_pillow()

    if not SOURCE_ICNS.is_file():
        print(f"Missing {SOURCE_ICNS} — install Signal Desktop for macOS.", file=sys.stderr)
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    base = _load_base_rgba(SOURCE_ICNS)

    for slug, _label in LAUNCHER_ICON_CHOICES:
        rgb = ICON_BUILD_TINTS.get(slug)
        dest = OUT_DIR / f"{slug}.icns"
        if rgb is None:
            shutil.copy2(SOURCE_ICNS, dest)
            print(f"OK {dest.name} (original)")
            continue

        tinted = _tint_rgba(base, rgb)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            tinted.save(tmp_path, "PNG")
            _png_to_icns(tmp_path, dest)
            print(f"OK {dest.name} (tint)")
        finally:
            tmp_path.unlink(missing_ok=True)

    print(f"\nDone. {len(LAUNCHER_ICON_CHOICES)} files in {OUT_DIR}")


if __name__ == "__main__":
    main()
