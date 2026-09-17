"""Load shared appearance settings and render a QR matrix without changing it."""

import io
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageColor, ImageDraw

MIN_QUIET_ZONE = 4
OPAQUE = 255
HEX_COLOR_LENGTH = 7
CONFIG_PATH = Path(__file__).with_name("appearances.json")


def load_settings(path: Path = CONFIG_PATH) -> dict[str, Any]:
    settings = json.loads(path.read_text())
    if settings["quietZone"] < MIN_QUIET_ZONE or settings["scale"] < 1:
        raise ValueError("Invalid QR image dimensions in appearances.json")
    ids = set()
    for preset in settings["presets"]:
        if preset["id"] in ids:
            raise ValueError("Duplicate appearance in appearances.json")
        ids.add(preset["id"])
        for key in ("ink", "paper"):
            color = preset[key]
            if len(color) != HEX_COLOR_LENGTH or not color.startswith("#"):
                raise ValueError("Appearance colors must be six-digit hex colors")
            ImageColor.getrgb(color)
        if not 0 <= preset["paperAlpha"] <= OPAQUE:
            raise ValueError("Invalid opacity in appearances.json")
    if settings["defaultPreset"] not in ids:
        raise ValueError("Unknown default appearance")
    return settings


SETTINGS = load_settings()
DEFAULT_PRESET = SETTINGS["defaultPreset"]
PRESETS = {preset["id"]: preset for preset in SETTINGS["presets"]}


def validate_dimensions(size: int, scale: int, border: int) -> None:
    if size < 1 or scale < 1 or border < SETTINGS["quietZone"]:
        raise ValueError(
            "Use a positive scale and at least four modules of clear margin."
        )


def png_bytes(matrix, size, scale, border, preset) -> bytes:
    validate_dimensions(size, scale, border)
    dimension = (size + 2 * border) * scale
    alpha = preset["paperAlpha"]
    mode = "RGB" if alpha == OPAQUE else "RGBA"
    paper = ImageColor.getrgb(preset["paper"])
    ink = ImageColor.getrgb(preset["ink"])
    if mode == "RGBA":
        paper = (*paper, alpha)
        ink = (*ink, OPAQUE)
    image = Image.new(mode, (dimension, dimension), paper)
    draw = ImageDraw.Draw(image)
    for row in range(size):
        for col in range(size):
            if matrix[row][col]:
                x = (col + border) * scale
                y = (row + border) * scale
                draw.rectangle((x, y, x + scale - 1, y + scale - 1), fill=ink)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def svg_bytes(matrix, size, scale, border, preset) -> bytes:
    validate_dimensions(size, scale, border)
    dimension = size + 2 * border
    pixels = dimension * scale
    path = " ".join(
        f"M{col + border},{row + border}h1v1h-1z"
        for row in range(size)
        for col in range(size)
        if matrix[row][col]
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{pixels}" height="{pixels}" viewBox="0 0 {dimension} {dimension}" '
        'shape-rendering="crispEdges">'
        f'<rect width="100%" height="100%" fill="{preset["paper"]}" '
        f'fill-opacity="{preset["paperAlpha"] / OPAQUE}"/>'
        f'<path fill="{preset["ink"]}" d="{path}"/></svg>'
    )
    return svg.encode("utf-8")


def write_svg(matrix, size, filename, *, preset=DEFAULT_PRESET, overwrite=False):
    data = svg_bytes(
        matrix, size, SETTINGS["scale"], SETTINGS["quietZone"], PRESETS[preset]
    )
    with Path(filename).open("wb" if overwrite else "xb") as output:
        output.write(data)
    print(f"Saved: {filename} (SVG)")
    return filename
