"""SOLMARA - a travel poster for a place that does not exist.

A standalone Python 3 renderer. It draws one 1024x1024 poster from scratch --
sky, sun, ridgelines, a sea arch, open water and type -- using only the
standard library (zlib, struct, math): a compact 5x7 bitmap alphabet, a few
pixel primitives and a minimal PNG encoder. No third-party modules, no fonts
and no network. Every coordinate, colour and loop is fixed, so two runs write
the same bytes.

The finished image goes to /output/entry.png (or $MAKEFUN_OUTPUT_DIR).
"""

import math
import os
import struct
import zlib

W = H = 1024
HORIZON = 600

# --- palette -----------------------------------------------------------------
INK = (10, 20, 40)
SKY_STOPS = [
    (0, (10, 20, 40)),
    (260, (26, 62, 88)),
    (450, (74, 116, 132)),
    (545, (226, 164, 96)),
    (600, (255, 208, 132)),
]
SUN = (255, 232, 170)
GLOW = (255, 186, 104)
RIDGE_FAR = (54, 86, 106)
RIDGE_NEAR = (32, 54, 74)
SEA_TOP = (36, 86, 108)
SEA_BOT = (14, 40, 58)
LANDMARK = (14, 26, 42)
LANDMARK_RIM = (86, 116, 138)
ROCK = (8, 16, 28)
TYPE = (250, 241, 222)
BOAT = (18, 32, 48)

# Capitals, digits and the few marks the poster needs, as seven rows of five.
GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000",) * 7,
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
}


# --- primitives --------------------------------------------------------------
def put(pix, x, y, rgb):
    if 0 <= x < W and 0 <= y < H:
        o = (y * W + x) * 3
        pix[o] = rgb[0]
        pix[o + 1] = rgb[1]
        pix[o + 2] = rgb[2]


def get(pix, x, y):
    o = (y * W + x) * 3
    return pix[o], pix[o + 1], pix[o + 2]


def rect(pix, x, y, w, h, rgb):
    """A solid rectangle, clipped to the canvas."""
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    band = bytes(rgb) * (x1 - x0)
    for row in range(y0, y1):
        base = (row * W + x0) * 3
        pix[base:base + (x1 - x0) * 3] = band


def disc(pix, cx, cy, radius, rgb):
    """A filled circle."""
    for dy in range(-radius, radius + 1):
        half = int((radius * radius - dy * dy) ** 0.5)
        rect(pix, cx - half, cy + dy, half * 2 + 1, 1, rgb)


def annulus(pix, cx, cy, r_in, r_out, rgb, top_only=False):
    """A ring of the given inner and outer radii."""
    lo2, hi2 = r_in * r_in, r_out * r_out
    for dy in range(-r_out, r_out + 1):
        y = cy + dy
        if top_only and dy > 0:
            break
        if not (0 <= y < H):
            continue
        half = int((hi2 - dy * dy) ** 0.5)
        for dx in range(-half, half + 1):
            d2 = dx * dx + dy * dy
            if lo2 <= d2 <= hi2:
                put(pix, cx + dx, y, rgb)


def poly(pix, pts, rgb):
    """Fill a polygon by even-odd scanline."""
    ys = [p[1] for p in pts]
    y0, y1 = max(0, int(math.floor(min(ys)))), min(H - 1, int(math.ceil(max(ys))))
    n = len(pts)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            if ay == by:
                continue
            if (ay <= y < by) or (by <= y < ay):
                xs.append(ax + (y - ay) * (bx - ax) / (by - ay))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            xa, xb = int(math.ceil(xs[i])), int(math.floor(xs[i + 1]))
            rect(pix, xa, y, xb - xa + 1, 1, rgb)


def glow(pix, cx, cy, radius, rgb, strength):
    """Blend existing pixels toward rgb, falling off with distance."""
    for dy in range(-radius, radius + 1):
        y = cy + dy
        if not (0 <= y < H):
            continue
        half = int((radius * radius - dy * dy) ** 0.5)
        for dx in range(-half, half + 1):
            x = cx + dx
            if not (0 <= x < W):
                continue
            d = (dx * dx + dy * dy) ** 0.5
            w = (1.0 - d / radius) ** 2 * strength
            if w <= 0.0:
                continue
            r, g, b = get(pix, x, y)
            put(pix, x, y, (
                int(r + (rgb[0] - r) * w),
                int(g + (rgb[1] - g) * w),
                int(b + (rgb[2] - b) * w),
            ))


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def label(pix, x, y, text, cw, ch, gap, rgb):
    """Draw condensed capitals; return the x just past the last glyph."""
    for ch_ in text.upper():
        rows = GLYPHS.get(ch_, GLYPHS[" "])
        for dy, bits in enumerate(rows):
            for dx, on in enumerate(bits):
                if on == "1":
                    rect(pix, x + dx * cw, y + dy * ch, cw, ch, rgb)
        x += 5 * cw + gap
    return x


# --- the poster --------------------------------------------------------------
def sky(pix):
    for y in range(HORIZON + 2):
        col = SKY_STOPS[-1][1]
        for i in range(len(SKY_STOPS) - 1):
            y0, c0 = SKY_STOPS[i]
            y1, c1 = SKY_STOPS[i + 1]
            if y0 <= y <= y1:
                col = lerp(c0, c1, (y - y0) / (y1 - y0))
                break
        rect(pix, 0, y, W, 1, col)


def sun(pix):
    glow(pix, 512, 548, 360, GLOW, 0.9)
    disc(pix, 512, 538, 94, SUN)
    disc(pix, 512, 538, 84, (255, 244, 202))


def ridges(pix):
    far = [(-20, HORIZON + 4)]
    for x, y in [(0, 498), (100, 512), (190, 486), (280, 512), (360, 528),
                 (440, 540), (512, 548), (584, 540), (664, 526), (744, 508),
                 (830, 484), (920, 510), (1024, 494)]:
        far.append((x, y))
    far.append((1060, HORIZON + 4))
    poly(pix, far, RIDGE_FAR)

    near = [(-20, HORIZON + 4)]
    for x, y in [(0, 552), (110, 534), (200, 552), (300, 566), (390, 574),
                 (512, 580), (630, 574), (720, 562), (810, 548), (900, 534),
                 (1024, 548)]:
        near.append((x, y))
    near.append((1060, HORIZON + 4))
    poly(pix, near, RIDGE_NEAR)


def sea(pix):
    for y in range(HORIZON, H):
        t = (y - HORIZON) / (H - HORIZON)
        base = lerp(SEA_TOP, SEA_BOT, t)
        for x in range(W):
            w = math.sin(x * 0.021 + y * 0.5) + 0.5 * math.sin(x * 0.05 - y * 0.9)
            k = 0.5 + 0.5 * w
            col = (
                min(255, int(base[0] + 16 * k)),
                min(255, int(base[1] + 22 * k)),
                min(255, int(base[2] + 26 * k)),
            )
            o = (y * W + x) * 3
            pix[o] = col[0]
            pix[o + 1] = col[1]
            pix[o + 2] = col[2]
    # the sun's broken shimmer on the water
    for y in range(HORIZON + 4, H, 5):
        t = (y - HORIZON) / (H - HORIZON)
        half = int(14 + 104 * t)
        for x in range(512 - half, 512 + half):
            if not (0 <= x < W) or ((x * 5 + y * 7) % 6) >= 3:
                continue
            f = 1.0 - abs(x - 512) / half
            r, g, b = get(pix, x, y)
            put(pix, x, y, (
                min(255, int(r + 118 * f)),
                min(255, int(g + 92 * f)),
                min(255, int(b + 44 * f)),
            ))


def landmark(pix):
    cx, cy, r_out, r_in = 512, HORIZON - 4, 246, 158
    # legs standing in the water
    rect(pix, cx - r_out, cy, r_out - r_in, 176, LANDMARK)
    rect(pix, cx + r_in, cy, r_out - r_in, 176, LANDMARK)
    # tapered feet
    poly(pix, [(cx - r_out, cy + 176), (cx - r_out + 40, cy), (cx - r_in + 20, cy), (cx - r_in + 46, cy + 176)], LANDMARK)
    poly(pix, [(cx + r_in - 20, cy), (cx + r_out - 40, cy), (cx + r_out - 46, cy + 176), (cx + r_in + 20, cy + 176)], LANDMARK)
    # the arch itself
    annulus(pix, cx, cy, r_in, r_out, LANDMARK, top_only=True)
    annulus(pix, cx, cy, r_in, r_in + 8, LANDMARK_RIM, top_only=True)


def boat(pix):
    poly(pix, [(250, 726), (330, 726), (318, 744), (262, 744)], BOAT)
    rect(pix, 288, 660, 4, 66, BOAT)
    poly(pix, [(292, 664), (292, 716), (334, 716)], BOAT)


def birds(pix):
    for bx, by, s in ((690, 300, 16), (742, 332, 12), (654, 344, 10), (800, 286, 9)):
        for i in range(s):
            put(pix, bx + i, by + abs(i - s // 2) // 1, TYPE)
            put(pix, bx + i, by + abs(i - s // 2) // 1 + 1, TYPE)
            put(pix, bx + 2 * s - i, by + abs(i - s // 2) // 1, TYPE)
            put(pix, bx + 2 * s - i, by + abs(i - s // 2) // 1 + 1, TYPE)


def foreground(pix):
    poly(pix, [(0, H), (0, 904), (120, 940), (250, 984), (300, H)], ROCK)
    poly(pix, [(W, H), (W, 912), (896, 948), (760, 990), (720, H)], ROCK)


def title(pix):
    text = "SOLMARA"
    cw, ch, gap = 14, 19, 11
    width = len(text) * (5 * cw + gap) - gap
    x0 = (W - width) // 2
    y0 = 66
    label(pix, x0 + 5, y0 + 6, text, cw, ch, gap, INK)
    label(pix, x0, y0, text, cw, ch, gap, TYPE)
    rule_y = y0 + 7 * ch + 26
    rect(pix, x0 + 6, rule_y, width - 12, 3, TYPE)
    rect(pix, x0 + 6, rule_y + 12, width - 12, 1, (196, 184, 160))


def compose(pix):
    sky(pix)
    sun(pix)
    ridges(pix)
    sea(pix)
    landmark(pix)
    boat(pix)
    birds(pix)
    foreground(pix)
    title(pix)


def png(pix):
    scanlines = bytearray()
    for row in range(H):
        scanlines.append(0)
        scanlines += pix[row * W * 3:(row + 1) * W * 3]

    def block(tag, payload):
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    body = zlib.compress(bytes(scanlines), 9)
    return b"\x89PNG\r\n\x1a\n" + block(b"IHDR", header) + block(b"IDAT", body) + block(b"IEND", b"")


def run():
    pix = bytearray(W * H * 3)
    compose(pix)
    data = png(pix)
    place = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(place, exist_ok=True)
    with open(os.path.join(place, "entry.png"), "wb") as handle:
        handle.write(data)
    print("entry.png: %d bytes" % len(data))


if __name__ == "__main__":
    run()
