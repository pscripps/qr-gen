#!/usr/bin/env python3
"""
Pure-Python QR Code generator (byte mode, EC level L).
Outputs PNG via PIL.  No network or third-party QR libraries needed.
"""

import argparse
import io
import sys
from pathlib import Path

from PIL import Image

DEFAULT_OUTPUT = "qrcode.png"
DEFAULT_SCALE = 10
QUIET_ZONE = 4
MAX_INPUT_BYTES = 2953

# ═══════════════════════════════════════════════════════════════════════════
#  GF(256) arithmetic  (primitive poly 0x11d)
# ═══════════════════════════════════════════════════════════════════════════
GF_EXP = [0] * 512
GF_LOG = [0] * 256


def _init_gf():
    x = 1
    for i in range(255):
        GF_EXP[i] = x
        GF_LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        GF_EXP[i] = GF_EXP[i - 255]


_init_gf()


def gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return GF_EXP[GF_LOG[a] + GF_LOG[b]]


def gf_poly_mul(p, q):
    r = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            r[i + j] ^= gf_mul(a, b)
    return r


def rs_generator(nsym):
    g = [1]
    for i in range(nsym):
        g = gf_poly_mul(g, [1, GF_EXP[i]])
    return g


def rs_encode(data, nsym):
    gen = rs_generator(nsym)
    msg = data[:] + [0] * nsym
    for i in range(len(data)):
        coef = msg[i]
        if coef != 0:
            for j in range(len(gen)):
                msg[i + j] ^= gf_mul(gen[j], coef)
    return msg[len(data) :]


# ═══════════════════════════════════════════════════════════════════════════
#  QR version / EC tables   (Level L, versions 1-40)
# ═══════════════════════════════════════════════════════════════════════════
# (total_data_cw, ec_per_block, nb1, dw1, nb2, dw2)
VERSION_TABLE_L = {
    1: (19, 7, 1, 19, 0, 0),
    2: (34, 10, 1, 34, 0, 0),
    3: (55, 15, 1, 55, 0, 0),
    4: (80, 20, 1, 80, 0, 0),
    5: (108, 26, 1, 108, 0, 0),
    6: (136, 18, 2, 68, 0, 0),
    7: (156, 20, 2, 78, 0, 0),
    8: (194, 24, 2, 97, 0, 0),
    9: (232, 30, 2, 116, 0, 0),
    10: (274, 18, 2, 68, 2, 69),
    11: (324, 20, 4, 81, 0, 0),
    12: (370, 24, 2, 92, 2, 93),
    13: (428, 26, 4, 107, 0, 0),
    14: (461, 30, 3, 115, 1, 116),
    15: (523, 22, 5, 87, 1, 88),
    16: (589, 24, 5, 98, 1, 99),
    17: (647, 28, 1, 107, 5, 108),
    18: (721, 30, 5, 120, 1, 121),
    19: (795, 28, 3, 113, 4, 114),
    20: (861, 28, 3, 107, 5, 108),
    21: (932, 28, 4, 116, 4, 117),
    22: (1006, 28, 2, 111, 7, 112),
    23: (1094, 30, 4, 121, 5, 122),
    24: (1174, 30, 6, 117, 4, 118),
    25: (1276, 26, 8, 106, 4, 107),
    26: (1370, 28, 10, 114, 2, 115),
    27: (1468, 30, 8, 122, 4, 123),
    28: (1531, 30, 3, 117, 10, 118),
    29: (1631, 30, 7, 116, 7, 117),
    30: (1735, 30, 5, 115, 10, 116),
    31: (1843, 30, 13, 115, 3, 116),
    32: (1955, 30, 17, 115, 0, 0),
    33: (2071, 30, 17, 115, 1, 116),
    34: (2191, 30, 13, 115, 6, 116),
    35: (2306, 30, 12, 121, 7, 122),
    36: (2434, 30, 6, 121, 14, 122),
    37: (2566, 30, 17, 122, 4, 123),
    38: (2702, 30, 4, 122, 18, 123),
    39: (2812, 30, 20, 117, 4, 118),
    40: (2956, 30, 19, 118, 6, 119),
}

ALIGNMENT_POSITIONS = {
    1: [],
    2: [6, 18],
    3: [6, 22],
    4: [6, 26],
    5: [6, 30],
    6: [6, 34],
    7: [6, 22, 38],
    8: [6, 24, 42],
    9: [6, 26, 46],
    10: [6, 28, 50],
    11: [6, 30, 54],
    12: [6, 32, 58],
    13: [6, 34, 62],
    14: [6, 26, 46, 66],
    15: [6, 26, 48, 70],
    16: [6, 26, 50, 74],
    17: [6, 30, 54, 78],
    18: [6, 30, 56, 82],
    19: [6, 30, 58, 86],
    20: [6, 34, 62, 90],
    21: [6, 28, 50, 72, 94],
    22: [6, 26, 50, 74, 98],
    23: [6, 30, 54, 78, 102],
    24: [6, 28, 54, 80, 106],
    25: [6, 32, 58, 84, 110],
    26: [6, 30, 58, 86, 114],
    27: [6, 34, 62, 90, 118],
    28: [6, 26, 50, 74, 98, 122],
    29: [6, 30, 54, 78, 102, 126],
    30: [6, 26, 52, 78, 104, 130],
    31: [6, 30, 56, 82, 108, 134],
    32: [6, 34, 60, 86, 112, 138],
    33: [6, 30, 58, 86, 114, 142],
    34: [6, 34, 62, 90, 118, 146],
    35: [6, 30, 54, 78, 102, 126, 150],
    36: [6, 24, 50, 76, 102, 128, 154],
    37: [6, 28, 54, 80, 106, 132, 158],
    38: [6, 32, 58, 84, 110, 136, 162],
    39: [6, 26, 54, 82, 110, 138, 166],
    40: [6, 30, 58, 86, 114, 142, 170],
}


def cci_bits(version):
    return 8 if version <= 9 else 16


def qr_size(version):
    return 17 + 4 * version


# ═══════════════════════════════════════════════════════════════════════════
#  Bit-stream
# ═══════════════════════════════════════════════════════════════════════════
class BitStream:
    def __init__(self):
        self.bits = []

    def put(self, value, length):
        for i in range(length - 1, -1, -1):
            self.bits.append((value >> i) & 1)

    def to_bytes(self):
        while len(self.bits) % 8:
            self.bits.append(0)
        result = []
        for i in range(0, len(self.bits), 8):
            b = 0
            for j in range(8):
                b = (b << 1) | self.bits[i + j]
            result.append(b)
        return result


# ═══════════════════════════════════════════════════════════════════════════
#  Encode data
# ═══════════════════════════════════════════════════════════════════════════
def choose_version(data_bytes):
    n = len(data_bytes)
    if not n:
        raise ValueError("Enter a URL or some text to turn into a QR code.")
    for v in range(1, 41):
        cap = VERSION_TABLE_L[v][0]
        total_bits = 4 + cci_bits(v) + n * 8
        total_bytes_needed = (total_bits + 7) // 8
        if total_bytes_needed <= cap:
            return v
    raise ValueError(
        f"Input is too long ({n} UTF-8 bytes). Maximum: {MAX_INPUT_BYTES} bytes. "
        "Try a shorter URL or less text."
    )


def encode_data(data_bytes, version):
    info = VERSION_TABLE_L[version]
    total_data_cw = info[0]
    bs = BitStream()
    bs.put(0b0100, 4)  # byte mode
    bs.put(len(data_bytes), cci_bits(version))
    for b in data_bytes:
        bs.put(b, 8)
    terminator_len = min(4, total_data_cw * 8 - len(bs.bits))
    bs.put(0, terminator_len)
    codewords = bs.to_bytes()
    pad_patterns = [0xEC, 0x11]
    i = 0
    while len(codewords) < total_data_cw:
        codewords.append(pad_patterns[i % 2])
        i += 1
    return codewords[:total_data_cw]


# ═══════════════════════════════════════════════════════════════════════════
#  Error correction
# ═══════════════════════════════════════════════════════════════════════════
def add_ecc(data_codewords, version):
    info = VERSION_TABLE_L[version]
    _, ec_per_block, nb1, dw1, nb2, dw2 = info
    blocks_data = []
    blocks_ecc = []
    offset = 0
    for _ in range(nb1):
        block = data_codewords[offset : offset + dw1]
        offset += dw1
        blocks_data.append(block)
        blocks_ecc.append(rs_encode(block, ec_per_block))
    for _ in range(nb2):
        block = data_codewords[offset : offset + dw2]
        offset += dw2
        blocks_data.append(block)
        blocks_ecc.append(rs_encode(block, ec_per_block))
    result = []
    max_dw = max(dw1, dw2) if nb2 else dw1
    for i in range(max_dw):
        for block in blocks_data:
            if i < len(block):
                result.append(block[i])
    for i in range(ec_per_block):
        for block in blocks_ecc:
            result.append(block[i])
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  Matrix construction
# ═══════════════════════════════════════════════════════════════════════════
def make_matrix(version):
    size = qr_size(version)
    matrix = [[None] * size for _ in range(size)]
    reserved = [[False] * size for _ in range(size)]
    return matrix, reserved, size


def place_finder(matrix, reserved, size, row, col):
    for r in range(-1, 8):
        for c in range(-1, 8):
            rr, cc = row + r, col + c
            if 0 <= rr < size and 0 <= cc < size:
                if 0 <= r <= 6 and 0 <= c <= 6:
                    if r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4):
                        matrix[rr][cc] = True
                    else:
                        matrix[rr][cc] = False
                else:
                    matrix[rr][cc] = False
                reserved[rr][cc] = True


def place_alignment(matrix, reserved, size, version):
    positions = ALIGNMENT_POSITIONS[version]
    if not positions:
        return
    for r in positions:
        for c in positions:
            if reserved[r][c]:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    rr, cc = r + dr, c + dc
                    if abs(dr) == 2 or abs(dc) == 2 or (dr == 0 and dc == 0):
                        matrix[rr][cc] = True
                    else:
                        matrix[rr][cc] = False
                    reserved[rr][cc] = True


def place_timing(matrix, reserved, size):
    for i in range(8, size - 8):
        val = i % 2 == 0
        if not reserved[6][i]:
            matrix[6][i] = val
            reserved[6][i] = True
        if not reserved[i][6]:
            matrix[i][6] = val
            reserved[i][6] = True


def place_dark_module(matrix, reserved, version):
    matrix[4 * version + 9][8] = True
    reserved[4 * version + 9][8] = True


def reserve_format_areas(reserved, size, version):
    for i in range(9):
        reserved[8][i] = True
        reserved[i][8] = True
    for i in range(8):
        reserved[8][size - 1 - i] = True
        reserved[size - 1 - i][8] = True
    if version >= 7:
        for i in range(6):
            for j in range(3):
                reserved[i][size - 11 + j] = True
                reserved[size - 11 + j][i] = True


def place_format_info(matrix, size, mask_id):
    ec_bits = 0b01  # Level L
    data = (ec_bits << 3) | mask_id
    remainder = data
    for _ in range(10):
        remainder <<= 1
        if remainder & (1 << 10):
            remainder ^= 0b10100110111
    info = (data << 10) | remainder
    info ^= 0b101010000010010

    bits = [(info >> i) & 1 for i in range(14, -1, -1)]

    # Horizontal strip near top-left
    positions_h = [
        (8, 0),
        (8, 1),
        (8, 2),
        (8, 3),
        (8, 4),
        (8, 5),
        (8, 7),
        (8, 8),
        (7, 8),
        (5, 8),
        (4, 8),
        (3, 8),
        (2, 8),
        (1, 8),
        (0, 8),
    ]
    for idx, (r, c) in enumerate(positions_h):
        matrix[r][c] = bool(bits[idx])

    # Vertical/horizontal strips near other finders
    positions_v = [
        (size - 1, 8),
        (size - 2, 8),
        (size - 3, 8),
        (size - 4, 8),
        (size - 5, 8),
        (size - 6, 8),
        (size - 7, 8),
        (8, size - 8),
        (8, size - 7),
        (8, size - 6),
        (8, size - 5),
        (8, size - 4),
        (8, size - 3),
        (8, size - 2),
        (8, size - 1),
    ]
    for idx, (r, c) in enumerate(positions_v):
        matrix[r][c] = bool(bits[idx])


def place_version_info(matrix, size, version):
    if version < 7:
        return
    data = version
    remainder = version
    for _ in range(12):
        remainder <<= 1
        if remainder & (1 << 12):
            remainder ^= 0b1111100100101
    info = (data << 12) | remainder
    k = 0
    for j in range(6):
        for i in range(3):
            bit = bool((info >> k) & 1)
            matrix[size - 11 + i][j] = bit
            matrix[j][size - 11 + i] = bit
            k += 1


# ═══════════════════════════════════════════════════════════════════════════
#  Data placement
# ═══════════════════════════════════════════════════════════════════════════
def place_data(matrix, reserved, size, data_bits):
    bit_idx = 0
    col = size - 1
    going_up = True
    while col >= 0:
        if col == 6:
            col -= 1
            continue
        rows = range(size - 1, -1, -1) if going_up else range(size)
        for row in rows:
            for dc in [0, -1]:
                c = col + dc
                if c < 0 or c >= size:
                    continue
                if reserved[row][c]:
                    continue
                if bit_idx < len(data_bits):
                    matrix[row][c] = bool(data_bits[bit_idx])
                else:
                    matrix[row][c] = False
                bit_idx += 1
        going_up = not going_up
        col -= 2


# ═══════════════════════════════════════════════════════════════════════════
#  Masking
# ═══════════════════════════════════════════════════════════════════════════
MASK_FUNCS = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]


def apply_mask(matrix, reserved, size, mask_id):
    func = MASK_FUNCS[mask_id]
    for r in range(size):
        for c in range(size):
            if not reserved[r][c] and matrix[r][c] is not None:
                if func(r, c):
                    matrix[r][c] = not matrix[r][c]


def score_matrix(matrix, size):
    score = 0
    # Rule 1
    for r in range(size):
        run = 1
        for c in range(1, size):
            if matrix[r][c] == matrix[r][c - 1]:
                run += 1
            else:
                if run >= 5:
                    score += run - 2
                run = 1
        if run >= 5:
            score += run - 2
    for c in range(size):
        run = 1
        for r in range(1, size):
            if matrix[r][c] == matrix[r - 1][c]:
                run += 1
            else:
                if run >= 5:
                    score += run - 2
                run = 1
        if run >= 5:
            score += run - 2
    # Rule 2
    for r in range(size - 1):
        for c in range(size - 1):
            v = matrix[r][c]
            if v == matrix[r][c + 1] == matrix[r + 1][c] == matrix[r + 1][c + 1]:
                score += 3
    # Rule 3
    pat1 = [True, False, True, True, True, False, True, False, False, False, False]
    pat2 = list(reversed(pat1))
    for r in range(size):
        for c in range(size - 10):
            row = [matrix[r][c + i] for i in range(11)]
            if row == pat1 or row == pat2:
                score += 40
    for c in range(size):
        for r in range(size - 10):
            col = [matrix[r + i][c] for i in range(11)]
            if col == pat1 or col == pat2:
                score += 40
    # Rule 4
    total = size * size
    dark = sum(1 for r in range(size) for c in range(size) if matrix[r][c])
    pct = dark * 100 // total
    prev5 = abs(pct - pct % 5 - 50) // 5
    next5 = abs(pct - pct % 5 + 5 - 50) // 5
    score += min(prev5, next5) * 10
    return score


# ═══════════════════════════════════════════════════════════════════════════
#  Main generation
# ═══════════════════════════════════════════════════════════════════════════
def generate_qr(url):
    data_bytes = url.encode("utf-8")
    version = choose_version(data_bytes)
    size = qr_size(version)
    print(f"QR Version: {version}, Size: {size}x{size}")

    data_codewords = encode_data(data_bytes, version)
    final_codewords = add_ecc(data_codewords, version)

    data_bits = []
    for cw in final_codewords:
        for i in range(7, -1, -1):
            data_bits.append((cw >> i) & 1)

    best_score = None
    best_matrix = None
    best_mask = None

    for mask_id in range(8):
        matrix, reserved, sz = make_matrix(version)
        place_finder(matrix, reserved, sz, 0, 0)
        place_finder(matrix, reserved, sz, 0, sz - 7)
        place_finder(matrix, reserved, sz, sz - 7, 0)
        place_alignment(matrix, reserved, sz, version)
        place_timing(matrix, reserved, sz)
        place_dark_module(matrix, reserved, version)
        reserve_format_areas(reserved, sz, version)
        place_data(matrix, reserved, sz, data_bits)
        apply_mask(matrix, reserved, sz, mask_id)
        place_format_info(matrix, sz, mask_id)
        place_version_info(matrix, sz, version)

        s = score_matrix(matrix, sz)
        if best_score is None or s < best_score:
            best_score = s
            best_matrix = [row[:] for row in matrix]
            best_mask = mask_id

    print(f"Best mask: {best_mask}, penalty: {best_score}")
    return best_matrix, size


def render_png(
    matrix,
    size,
    scale=DEFAULT_SCALE,
    border=QUIET_ZONE,
    filename=DEFAULT_OUTPUT,
    *,
    overwrite=False,
):
    img_size = (size + 2 * border) * scale
    img = Image.new("RGB", (img_size, img_size), "white")
    pixels = img.load()
    if pixels is None:
        raise ValueError("Could not initialize the PNG image.")
    for r in range(size):
        for c in range(size):
            if matrix[r][c]:
                for dy in range(scale):
                    for dx in range(scale):
                        py = (r + border) * scale + dy
                        px = (c + border) * scale + dx
                        pixels[px, py] = (0, 0, 0)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    with Path(filename).open("wb" if overwrite else "xb") as output:
        output.write(buffer.getvalue())
    print(f"Saved: {filename} ({img_size}x{img_size} px)")
    return filename


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Make a QR image locally. Everything stays on your computer.",
        epilog='Example: python3 qr_gen.py "https://example.com" mycode.png',
    )
    parser.add_argument("data", help="URL or text to encode; put it in quotes")
    parser.add_argument(
        "output",
        nargs="?",
        default=DEFAULT_OUTPUT,
        help=f"PNG output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--force", action="store_true", help="replace an existing output file"
    )
    args = parser.parse_args(argv)
    try:
        matrix, size = generate_qr(args.data)
        render_png(matrix, size, filename=args.output, overwrite=args.force)
    except FileExistsError:
        parser.exit(
            2,
            f"Error: {args.output} already exists. Choose another filename "
            "or use --force to replace it.\n",
        )
    except ValueError as error:
        parser.exit(2, f"Error: {error}\n")
    except OSError as error:
        parser.exit(
            2,
            f"Error: could not save {args.output}: {error.strerror or error}. "
            "Check that the folder exists and you can write to it.\n",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
