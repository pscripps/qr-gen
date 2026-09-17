"""Independently decode rasterized browser SVGs; used by the canonical gate."""

import json
import sys
from pathlib import Path

import zxingcpp
from PIL import Image


def verify(manifest: Path) -> None:
    for record in json.loads(manifest.read_text()):
        image = Image.open(record["path"]).convert("RGB")
        decoded = zxingcpp.read_barcode(image)
        if record["preset"] == "clear" and record["surface"] == "charcoal":
            # A permissive software decoder may read this low contrast sample.
            # It is deliberately not accepted as a supported deployment surface.
            continue
        if decoded is None or decoded.bytes != record["payload"].encode("utf-8"):
            raise AssertionError(f"Saved output did not round-trip: {record}")
    print(
        "Browser SVG exports decoded with exact UTF-8 payloads on supported surfaces."
    )


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
