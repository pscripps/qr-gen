# qr-gen

A small, dependency-light QR code generator written in pure Python (byte mode, error-correction level L, versions 1–40).

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
python3 qr_gen.py '<data>' [output.png]
```

Example:

```bash
python3 qr_gen.py 'https://example.com' mycode.png
```

If you omit the output path, it writes `qrcode.png` in the current directory.

## Note

This is a from-scratch QR implementation — the encoding, Reed–Solomon error
correction, masking, and matrix construction are all hand-rolled rather than
delegated to an established QR library. It supports **error-correction level L
only** (the lowest of the four levels, ~7% recovery). Always test-scan the
output with a real reader before relying on it for anything that matters.
