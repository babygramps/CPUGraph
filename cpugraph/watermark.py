"""Watermark utilities."""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Optional

from PIL import Image


def load_watermark_image(base_path: str | os.PathLike[str] | None = None) -> Optional[Image.Image]:
    """Load the Orbital watermark image if available.

    The loader prefers the PNG asset and falls back to the SVG version when
    CairoSVG is installed. The returned value is a ``PIL.Image`` instance in
    RGBA mode or ``None`` when no asset could be loaded.
    """

    search_path = Path(base_path or Path(__file__).resolve().parent)

    png_path = search_path / "OrbitalDarkPurple.png"
    if png_path.exists():
        return Image.open(png_path).convert("RGBA")

    svg_path = search_path / "OrbitalDarkPurple.svg"
    if svg_path.exists():
        try:
            import cairosvg

            png_bytes = cairosvg.svg2png(url=str(svg_path), output_width=800)
            return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        except Exception:
            return None

    return None
