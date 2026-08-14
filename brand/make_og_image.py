#!/usr/bin/env python3
"""Render the canonical 1200x630 UniStay social card with macOS tools."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SVG = Path(__file__).with_name("og-image.svg")
OUTPUT = ROOT / "public/og-image.png"

with tempfile.TemporaryDirectory(prefix="unistay-og-") as temporary:
    temp = Path(temporary)
    subprocess.run(["qlmanage", "-t", "-s", "1200", "-o", str(temp), str(SVG)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rendered = temp / f"{SVG.name}.png"
    subprocess.run(["sips", "-z", "630", "1200", str(rendered), "--out", str(temp / "og-image.png")], check=True, stdout=subprocess.DEVNULL)
    shutil.copy2(temp / "og-image.png", OUTPUT)

print(OUTPUT)
