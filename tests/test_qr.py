"""Round-trip the actual PNGs and test user-visible command behavior."""

import contextlib
import io
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import qrcode
import zxingcpp
from PIL import Image
from qrcode import constants, util

import qr_gen

SCRIPT = Path(qr_gen.__file__).resolve()


class QRTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.directory = Path(self.folder.name)

    def command(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.directory,
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_decodes(self, path, text):
        with Image.open(path) as image:
            self.assertEqual(image.format, "PNG")
            result = zxingcpp.read_barcode(image)
        self.assertIsNotNone(result)
        self.assertEqual(result.bytes, text.encode("utf-8"))

    def test_default_and_explicit_output(self):
        for text, filename in [
            ("https://example.com", "qrcode.png"),
            (" café 日本語 😀 ", "name with spaces.png"),
        ]:
            args = [text] if filename == "qrcode.png" else [text, filename]
            result = self.command(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_decodes(self.directory / filename, text)

    def test_help_does_not_generate(self):
        result = self.command("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--force", result.stdout)
        self.assertFalse((self.directory / "qrcode.png").exists())

    def test_existing_file_is_preserved_and_force_replaces(self):
        path = self.directory / "qrcode.png"
        original = b"An existing file that must survive."
        path.write_bytes(original)
        result = self.command("https://example.com")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)
        self.assertEqual(path.read_bytes(), original)
        result = self.command("https://example.com", "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_decodes(path, "https://example.com")

    def test_input_errors_do_not_leave_output(self):
        for args, message in [
            ([], "required"),
            ([""], "Enter a URL"),
            (["x" * 2954], "too long"),
            (["😀" * 739], "too long"),
            (["url", "a.png", "unexpected"], "unrecognized"),
        ]:
            with self.subTest(args_length=len(args), message=message):
                result = self.command(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse((self.directory / "qrcode.png").exists())

    def test_unwritable_destination_is_explained(self):
        for output in ["missing/code.png", str(self.directory)]:
            result = self.command("https://example.com", output, "--force")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("could not save", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_all_version_boundaries_match_reference_and_decode(self):
        rng = random.Random(1729)
        previous_capacity = 0
        for version in range(1, 41):
            capacity = qr_gen.VERSION_TABLE_L[version][0] - (2 if version < 10 else 3)
            for length in [previous_capacity + 1, capacity]:
                with self.subTest(version=version, length=length):
                    text = "".join(
                        rng.choice("abcdef0123456789:/?&=") for _ in range(length)
                    )
                    with contextlib.redirect_stdout(io.StringIO()):
                        matrix, size = qr_gen.generate_qr(text)
                        path = self.directory / "boundary.png"
                        qr_gen.render_png(matrix, size, filename=path, overwrite=True)
                    self.assertEqual(size, qr_gen.qr_size(version))
                    self.assert_decodes(path, text)
                    matched = False
                    for mask in range(8):
                        reference = qrcode.QRCode(
                            version=version,
                            error_correction=constants.ERROR_CORRECT_L,
                            border=0,
                            mask_pattern=mask,
                        )
                        reference.add_data(
                            util.QRData(text.encode(), mode=util.MODE_8BIT_BYTE),
                            optimize=0,
                        )
                        reference.make(fit=False)
                        if reference.get_matrix() == matrix:
                            matched = True
                            break
                    self.assertTrue(matched, "matrix differs from every reference mask")
            previous_capacity = capacity


if __name__ == "__main__":
    unittest.main()
