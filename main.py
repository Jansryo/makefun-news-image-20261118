"""Shared renderer for make.fun 'Sum up world news in one image' entries.

Python 3.13 stdlib only (os / struct / zlib). No network, no time, no
randomness, no third-party packages. Output is fully deterministic:
identical input bytes -> identical PNG bytes (fixed zlib level, no
ancillary chunks, no timestamps).

Layout: 1024x1024 dark newspaper poster. Masthead + date, then one row
per story: colour-coded category chip, bold headline, one summary.
"""

import os
import struct
import zlib

W, H = 1024, 1024
MARGIN = 48
CONTENT_W = W - 2 * MARGIN  # 928

BG = (11, 18, 32)
WHITE = (235, 238, 242)
MUTED = (167, 180, 196)
DIM = (91, 107, 128)
GOLD = (250, 176, 5)
SEPARATOR = (27, 39, 64)

CAT_COLORS = {
    "CONFLICT": (255, 107, 107),
    "DIPLOMACY": (77, 171, 247),
    "ECONOMY": (105, 219, 124),
    "DEFENSE": (255, 169, 77),
}

# ---------------------------------------------------------------- font 5x7
# Each glyph is 7 rows of 5 chars; '#' = pixel on. ASCII only.
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "a": (".....", ".....", ".###.", "....#", ".####", "#...#", ".####"),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    "f": ("..##.", ".#..#", ".#...", "###..", ".#...", ".#...", ".#..."),
    "g": (".....", ".....", ".####", "#...#", "#...#", ".####", "....#"),
    "h": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "i": (".....", "..#..", ".....", ".##..", "..#..", "..#..", ".###."),
    "j": ("...#.", ".....", "..##.", "...#.", "...#.", "...#.", ".##.."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    "n": (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (".....", ".....", "####.", "#...#", "#...#", "####.", "#...."),
    "q": (".....", ".....", ".####", "#...#", "#...#", ".####", "....#"),
    "r": (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    "t": (".#...", ".#...", "###..", ".#...", ".#...", ".#...", "..##."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#"),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (".....", ".....", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", "..#..", ".#..."),
    ";": (".....", ".##..", ".....", ".##..", ".##..", "..#..", ".#..."),
    ":": (".....", ".....", ".##..", ".....", ".##..", ".....", "....."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "%": ("#...#", "#..#.", "...#.", "..#..", ".#...", "#..#.", "#...#"),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.#.#", "#....", ".###."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "[": (".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
    "]": (".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
    "*": (".....", ".#.#.", "..#..", "#####", "..#..", ".#.#.", "....."),
    "<": ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    ">": (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    "~": (".....", ".....", ".##.#", "#.#.#", ".....", ".....", "....."),
    "^": ("..#..", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "|": ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "\\": ("#....", "#....", ".#...", "..#..", "...#.", "....#", "....#"),
    "{": ("..##.", ".#...", ".#...", "###..", ".#...", ".#...", "..##."),
    "}": (".##..", "...#.", "...#.", "..###", "...#.", "...#.", ".##.."),
    "`": (".#...", "..#..", ".....", ".....", ".....", ".....", "....."),
}


def text_w(s, scale):
    """Pixel width of s at scale (6 px advance per char, no trailing gap)."""
    return len(s) * 6 * scale - scale if s else 0


def wrap(text, scale, max_w):
    """Greedy word wrap; returns list of lines that fit max_w pixels."""
    lines = []
    cur = ""
    for word in text.split(" "):
        trial = (cur + " " + word).strip()
        if text_w(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(bytes(bg) * (w * h))

    def px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            self.buf[base:base + len(row)] = row

    def glyph(self, ch, x, y, scale, color, bold=False):
        rows = FONT.get(ch)
        if rows is None:
            rows = FONT["?"]
        for r, row in enumerate(rows):
            for c, p in enumerate(row):
                if p == "#":
                    for dy in range(scale):
                        for dx in range(scale):
                            self.px(x + c * scale + dx, y + r * scale + dy, color)
                            if bold:
                                self.px(x + c * scale + dx + 1,
                                        y + r * scale + dy, color)

    def text(self, s, x, y, scale, color, bold=False):
        cx = x
        for ch in s:
            self.glyph(ch, cx, y, scale, color, bold)
            cx += 6 * scale
        return cx

    def text_right(self, s, x_right, y, scale, color, bold=False):
        self.text(s, x_right - text_w(s, scale), y, scale, color, bold)


# ---------------------------------------------------------------- PNG output

def _chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return out


def write_png(path, cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.buf[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + _chunk(b"IEND", b""))
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- layout

def render(data):
    cv = Canvas(W, H, BG)
    cv.rect(0, 0, W, 10, GOLD)  # masthead accent bar
    cv.text("WORLD NEWS", MARGIN, 40, 6, WHITE, bold=True)
    cv.text(data["date"], MARGIN, 100, 2, GOLD)
    cv.text_right(data["count_label"], W - MARGIN, 100, 2, MUTED)
    cv.rect(MARGIN, 132, CONTENT_W, 2, SEPARATOR)

    y = 152
    items = data["items"]
    for i, it in enumerate(items):
        color = CAT_COLORS[it["cat"]]
        cv.rect(MARGIN, y + 4, 12, 12, color)
        cv.text(it["cat"], MARGIN + 20, y + 2, 2, color, bold=True)
        cv.text_right("%02d" % (i + 1), W - MARGIN, y + 2, 3, DIM, bold=True)

        hy = y + 28
        for ln in wrap(it["headline"], 3, CONTENT_W):
            cv.text(ln, MARGIN, hy, 3, WHITE, bold=True)
            hy += 25
        sy = hy + 6
        for ln in wrap(it["summary"], 2, CONTENT_W):
            cv.text(ln, MARGIN, sy, 2, MUTED)
            sy += 17
        if i < len(items) - 1:
            cv.rect(MARGIN, y + 119, CONTENT_W, 1, SEPARATOR)
        y += 120

    cv.text("SUMMARY OF THE DAY'S TOP STORIES", MARGIN, 998, 2, DIM)
    return cv


def main(data):
    """Write the poster to /output/entry.png (bounty path) and to
    ./output/entry.png next to this script (preview copy)."""
    cv = render(data)
    here = os.path.dirname(os.path.abspath(__file__))
    wrote = []
    for path in ("/output/entry.png",
                 os.path.join(here, "output", "entry.png")):
        try:
            write_png(path, cv)
            wrote.append(path)
        except OSError:
            pass
    if not wrote:
        raise OSError("could not write output/entry.png anywhere")
    print("wrote " + ", ".join(wrote))


DATA = {
    "date": "WEDNESDAY, 18 NOVEMBER 2026",
    "count_label": "7 TOP STORIES",
    "items": [
        {
            "cat": "DIPLOMACY",
            "headline": "APEC Summit opens in Shenzhen",
            "summary": "Leaders gather in China for the APEC Summit, running 18-19 November.",
        },
        {
            "cat": "DIPLOMACY",
            "headline": "Trump lands in Manila for QUAD talks",
            "summary": "The US president arrives for QUAD talks as the group announces a new plan.",
        },
        {
            "cat": "DIPLOMACY",
            "headline": "First Trump-Xi-Putin summit set for tomorrow",
            "summary": "The first-ever three-way summit takes place on Thursday 19 November in Shenzhen.",
        },
        {
            "cat": "CONFLICT",
            "headline": "Ukraine hits Crimean Bridge a second day",
            "summary": "Kyiv damages the bridge again as Russia pounds bridges across the Dnipro in Kyiv.",
        },
        {
            "cat": "CONFLICT",
            "headline": "Iran drones target US radar in Bahrain",
            "summary": "Kuwait reports drone interceptions and Bahrain issues an all-clear after the attack.",
        },
        {
            "cat": "CONFLICT",
            "headline": "Gaza ceasefire faces imminent collapse",
            "summary": "The Board of Peace warns the ceasefire is close to falling apart.",
        },
        {
            "cat": "ECONOMY",
            "headline": "Nvidia doubles revenue to $115.84B",
            "summary": "Quarterly revenue hits $115.84 billion, but the board will not reinstate Jensen Huang.",
        },
    ],
}


main(DATA)
