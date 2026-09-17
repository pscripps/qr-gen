"""Verify shared presets, real PNGs, alpha, quiet zones, and CLI export behavior."""

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import zxingcpp
from PIL import Image, ImageColor

import qr_gen
from qr_appearance import PRESETS, SETTINGS, png_bytes, svg_bytes

ROOT = Path(__file__).resolve().parents[1]


class AppearanceTests(unittest.TestCase):
    def test_png_outputs_keep_payload_and_margin(self):
        payload = "https://example.com/café/東京?x=%20&y=😀"
        with contextlib.redirect_stdout(io.StringIO()):
            matrix, size = qr_gen.generate_qr(payload)
        for preset in PRESETS.values():
            with self.subTest(preset=preset["id"]):
                image = Image.open(io.BytesIO(png_bytes(matrix, size, 10, 4, preset)))
                alpha = image.convert("RGBA").getchannel("A").getpixel((0, 0))
                self.assertEqual(alpha, preset["paperAlpha"])
                # Pixel dimensions retain the complete four-module border.
                self.assertEqual(image.width, (size + 8) * 10)
                for surface in SETTINGS["surfaces"]:
                    if preset["id"] == "clear" and surface["id"] == "charcoal":
                        continue
                    paper = Image.new("RGBA", image.size, surface["color"])
                    composited = Image.alpha_composite(paper, image.convert("RGBA"))
                    result = zxingcpp.read_barcode(composited.convert("RGB"))
                    self.assertIsNotNone(result)
                    self.assertEqual(result.bytes, payload.encode())
                expected = ImageColor.getrgb(preset["paper"])
                self.assertEqual(image.convert("RGB").getpixel((39, 39)), expected)

    def test_svg_preserves_margin_alpha_and_explicit_format(self):
        with contextlib.redirect_stdout(io.StringIO()):
            matrix, size = qr_gen.generate_qr("hello")
        for preset in PRESETS.values():
            svg = svg_bytes(matrix, size, 10, 4, preset).decode()
            self.assertIn(f'viewBox="0 0 {size + 8} {size + 8}"', svg)
            self.assertIn(f'fill-opacity="{preset["paperAlpha"] / 255}"', svg)
        with self.assertRaisesRegex(ValueError, "four modules"):
            png_bytes(matrix, size, 10, 3, PRESETS["classic"])

    def test_cli_presets_svg_and_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "code.svg"
            args = [
                sys.executable,
                str(ROOT / "qr_gen.py"),
                "https://example.com",
                str(output),
                "--preset",
                "reverse",
                "--format",
                "svg",
            ]
            result = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("supports inversion", result.stderr)
            self.assertTrue(output.read_text().startswith("<svg"))
            before = output.read_bytes()
            self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertEqual(before, output.read_bytes())
            self.assertEqual(
                subprocess.run([*args, "--force"], capture_output=True).returncode, 0
            )

    def test_svg_default_does_not_rename_explicit_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            command = [
                sys.executable,
                str(ROOT / "qr_gen.py"),
                "hello",
                "--format",
                "svg",
            ]
            result = subprocess.run(command, cwd=temporary, capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertTrue((Path(temporary) / "qrcode.svg").exists())
            result = subprocess.run(
                [*command, "qrcode.png"], cwd=temporary, capture_output=True
            )
            self.assertEqual(result.returncode, 0)
            self.assertTrue(
                (Path(temporary) / "qrcode.png").read_text().startswith("<svg")
            )
