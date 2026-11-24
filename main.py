#!/usr/bin/env python3
"""THE WORLD TODAY - front page for Tuesday 24 November 2026.

Draws a newspaper front page (1024x1024 PNG) summing up eight verified
world-news stories from 24 November 2026. Pure standard library: a small
built-in 5x7 bitmap font and a hand-rolled PNG encoder (zlib + CRC).
Deterministic: the same bytes on every run, no network, no clock, no
randomness anywhere.
"""

import os
import struct
import sys
import zlib

# ---------------------------------------------------------------- canvas

WIDTH = 1024
HEIGHT = 1024

PAPER = (248, 244, 233)   # warm newsprint
INK = (17, 24, 39)        # near-black headline ink
NAVY = (30, 58, 95)       # masthead blue
RED = (185, 28, 28)       # kicker red
GREY = (90, 90, 84)       # secondary text
RULE = (60, 60, 58)       # thin rule lines
SOFT = (232, 226, 210)    # pale panel fill


class Page:
    """A flat RGB canvas with rectangle and pixel helpers."""

    def __init__(self, width, height, colour):
        self.width = width
        self.height = height
        self.pixels = bytearray(colour * (width * height))

    def put(self, x, y, colour):
        if 0 <= x < self.width and 0 <= y < self.height:
            base = (y * self.width + x) * 3
            self.pixels[base:base + 3] = bytes(colour)

    def fill(self, x0, y0, x1, y1, colour):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.width, x1)
        y1 = min(self.height, y1)
        for yy in range(y0, y1):
            base = (yy * self.width + x0) * 3
            self.pixels[base:base + (x1 - x0) * 3] = bytes(colour) * (x1 - x0)

    def hline(self, x0, x1, y, colour, thickness=1):
        self.fill(x0, y, x1, y + thickness, colour)

    def vline(self, x, y0, y1, colour, thickness=1):
        self.fill(x, y0, x + thickness, y1, colour)


# ------------------------------------------------------------------- font

# Each glyph is seven rows of five bits, written as strings.
# Uppercase letters, digits and punctuation live on all seven rows;
# lowercase letters sit on the middle five rows, like small print.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
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
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01110", "10000", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "f": ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    "g": ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    "h": ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    "i": ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00110", "00010", "00010", "10010", "01100"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    "q": ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("01000", "01000", "11100", "01000", "01000", "01001", "00110"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "y": ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "~": ("00000", "00000", "01001", "10110", "00000", "00000", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
}

CHAR_W = 6  # five glyph columns plus one column of spacing
CHAR_H = 7


def text_width(text, scale):
    """Pixel width of a line at the given scale."""
    return len(text) * CHAR_W * scale


def draw_text(page, x, y, text, scale, colour):
    """Draw one line of text with its top-left corner at (x, y)."""
    for index, char in enumerate(text):
        glyph = FONT.get(char)
        if glyph is None:
            continue
        base_x = x + index * CHAR_W * scale
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    page.fill(base_x + col * scale, y + row * scale,
                              base_x + (col + 1) * scale,
                              y + (row + 1) * scale, colour)


def draw_centred(page, cx, y, text, scale, colour):
    draw_text(page, cx - text_width(text, scale) // 2, y, text, scale, colour)


def wrap(text, limit):
    """Greedy word wrap; returns a list of lines of at most `limit` chars."""
    lines = []
    current = ""
    for word in text.split(" "):
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= limit:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_block(page, x, y, width, lines, scale, colour, gap=2):
    """Draw wrapped lines stacked downwards; returns the y below them."""
    for line in lines:
        draw_text(page, x, y, line, scale, colour)
        y += CHAR_H * scale + gap
    return y


# -------------------------------------------------------------- PNG output

def png_bytes(page):
    """Encode the canvas as a deterministic RGB PNG (filter 0 rows)."""
    raw = bytearray()
    stride = page.width * 3
    for row in range(page.height):
        raw.append(0)
        start = row * stride
        raw += page.pixels[start:start + stride]
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        block = kind + data
        return (struct.pack(">I", len(data)) + block +
                struct.pack(">I", zlib.crc32(block) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", page.width, page.height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
            chunk(b"IDAT", compressed) + chunk(b"IEND", b""))


# ------------------------------------------------------------------ layout

MARGIN = 36
CONTENT_W = WIDTH - 2 * MARGIN


def draw_masthead(page):
    draw_centred(page, WIDTH // 2, 30, "THE WORLD TODAY", 6, NAVY)
    page.hline(MARGIN, WIDTH - MARGIN, 96, RULE, 3)
    page.hline(MARGIN, WIDTH - MARGIN, 102, RULE, 1)
    draw_centred(page, WIDTH // 2, 118, "TUESDAY 24 NOVEMBER 2026", 3, RED)
    draw_centred(page, WIDTH // 2, 150,
                 "The day's world news, in one page  -  eight stories",
                 1, GREY)


def draw_lead(page, y):
    """Lead story: Nvidia, full width, with a big market stat at right."""
    box_h = 196
    page.fill(MARGIN, y, WIDTH - MARGIN, y + box_h, SOFT)
    page.hline(MARGIN, WIDTH - MARGIN, y, NAVY, 4)
    page.hline(MARGIN, WIDTH - MARGIN, y + box_h - 1, NAVY, 2)
    text_x = MARGIN + 22
    draw_text(page, text_x, y + 18, "TECH  -  MARKETS", 1, RED)
    draw_text(page, text_x, y + 40, "HUANG RETURNS", 4, INK)
    draw_text(page, text_x, y + 72, "TO LEAD NVIDIA", 4, INK)
    deck = ("The board reinstates Jensen Huang as chief executive, 11 days "
            "after his resignation. Shares jump as Wall Street rallies and "
            "AI stocks recover.")
    draw_block(page, text_x, y + 116, 560, wrap(deck, 84), 1, INK, gap=3)
    # Market stat panel on the right of the lead box.
    stat_x = WIDTH - MARGIN - 250
    page.vline(stat_x - 18, y + 18, y + box_h - 18, RULE, 1)
    draw_text(page, stat_x, y + 30, "+31%", 6, NAVY)
    draw_text(page, stat_x, y + 84, "NVIDIA SHARES", 1, INK)
    draw_text(page, stat_x, y + 98, "IN A SINGLE DAY", 1, INK)
    draw_text(page, stat_x, y + 126, "S&P 500 +4.7%  -  NASDAQ +7%", 1, GREY)
    draw_text(page, stat_x, y + 144, "CHIP STOCKS LEAD", 1, GREY)
    draw_text(page, stat_x, y + 162, "THE REBOUND", 1, GREY)
    return y + box_h


def draw_card(page, x, y, width, height, kicker, headline, body):
    page.fill(x, y, x + width, y + height, (255, 255, 255))
    page.hline(x, x + width, y, RED, 3)
    page.vline(x, y, y + height, RULE, 1)
    page.vline(x + width - 1, y, y + height, RULE, 1)
    page.hline(x, x + width, y + height - 1, RULE, 1)
    inner = x + 14
    draw_text(page, inner, y + 12, kicker, 1, RED)
    draw_block(page, inner, y + 28, width - 28,
               wrap(headline, 37), 2, INK, gap=2)
    draw_block(page, inner, y + 28 + 2 * (CHAR_H * 2 + 2) + 2,
               width - 28, wrap(body, 74), 1, GREY, gap=3)


def draw_grid(page, y):
    """Seven story cards in two columns, plus a numbers box."""
    gap = 16
    card_w = (CONTENT_W - gap) // 2
    card_h = 118
    stories = [
        ("CONFLICT  -  LIBYA",
         "UKRAINE SINKS RUSSIAN WARSHIP OFF LIBYA",
         "Kyiv says seven naval drones sank the corvette Merkury at "
         "Benghazi, a rare strike far beyond the Black Sea."),
        ("UKRAINE WAR",
         "DEADLY STRIKE HITS ZAPORIZHZHIA",
         "An overnight Russian attack kills two and wounds about 40, "
         "including four children, hitting an apartment block."),
        ("MIDDLE EAST  -  GAZA",
         "HAMAS SECURITY CHIEF KILLED IN GAZA",
         "Israeli airstrikes kill Naeem Abu Nahel and six others, "
         "including two police officers, medics and police say."),
        ("ASIA  -  CHINA",
         "CHINA PROBES A POLITBURO MEMBER",
         "Shanghai party chief Chen Jining is under investigation, the "
         "fourth member of the top leadership probed since 2025."),
        ("DISASTER  -  INDONESIA",
         "FACTORY FIRE KILLS 26 IN INDONESIA",
         "A blaze in Banten leaves dozens missing as rescuers search "
         "the wreckage of the factory."),
        ("CLIMATE  -  COP31",
         "COP31 ENDS WITH NO FOSSIL-FUEL DEAL",
         "The climate summit closes with no agreement on phasing out "
         "fossil fuels, leaving the world divided."),
        ("MIGRATION  -  AFRICA",
         "175 MIGRANTS MISSING OFF SENEGAL",
         "Contact is lost with a Europe-bound boat that left Dakar "
         "about two weeks ago, officials say."),
    ]
    for index, (kicker, headline, body) in enumerate(stories):
        col = index % 2
        row = index // 2
        card_x = MARGIN + col * (card_w + gap)
        card_y = y + row * (card_h + gap)
        draw_card(page, card_x, card_y, card_w, card_h,
                  kicker, headline, body)
    # Numbers box fills the last grid cell (row 3, right column).
    box_x = MARGIN + card_w + gap
    box_y = y + 3 * (card_h + gap)
    page.fill(box_x, box_y, box_x + card_w, box_y + card_h, NAVY)
    draw_text(page, box_x + 16, box_y + 14, "THE DAY IN NUMBERS", 1,
              (255, 255, 255))
    draw_text(page, box_x + 16, box_y + 34, "31%  NVIDIA SHARES UP", 2,
              (255, 255, 255))
    draw_text(page, box_x + 16, box_y + 62, "103.3  US CONSUMER", 2,
              (255, 255, 255))
    draw_text(page, box_x + 16, box_y + 78, "CONFIDENCE, HIGHEST", 1,
              (200, 210, 225))
    draw_text(page, box_x + 16, box_y + 92, "IN NEARLY TWO YEARS", 1,
              (200, 210, 225))
    return y + 4 * card_h + 3 * gap


def draw_footer(page, y):
    page.hline(MARGIN, WIDTH - MARGIN, y, RULE, 2)
    draw_centred(page, WIDTH // 2, y + 14,
                 "Sources: Reuters, Associated Press, BBC, The Guardian, Xinhua",
                 1, GREY)
    draw_centred(page, WIDTH // 2, y + 32,
                 "All events of Tuesday 24 November 2026  -  THE WORLD TODAY",
                 1, GREY)


def build_page():
    page = Page(WIDTH, HEIGHT, PAPER)
    draw_masthead(page)
    after_lead = draw_lead(page, 186)
    after_grid = draw_grid(page, after_lead + 18)
    draw_footer(page, after_grid + 16)
    return page


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = png_bytes(build_page())
    target = os.path.join(out_dir, "entry.png")
    with open(target, "wb") as handle:
        handle.write(data)
    print(f"wrote {target} ({len(data)} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
