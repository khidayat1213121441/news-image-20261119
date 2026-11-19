#!/usr/bin/env python3
"""The World in One Image - 19 November 2026.

A procedural front page summing up 19 November 2026, drawn by a pure-Python
software 3D renderer written from scratch (stdlib only, no network, no
randomness, no time): a shaded 3D globe with glowing pins, an extruded neon
"VI" monogram for the GTA VI launch, and eight story panels, each with its
own small 3D scene - a 3D Capitol dome, 3D IPO bars, a 3D summit table, a
bridge with a collapsed span, an armoured column, a missile launch, a
cyclone spiral and the EU flag with coin stacks. Writes 1024x1024
entry.png to $MAKEFUN_OUTPUT_DIR. Deterministic: two runs write
identical bytes.

Stories (researched 19 Nov 2026, multi-source agreement):
  - GTA VI begins its worldwide rollout at midnight local time, from New
    Zealand: 13-year wait, $1bn+ production, ~16m copies / $1.5bn pre-sales,
    Metacritic 99, PS5 / Xbox Series X|S, $79.99 / $99.99 (Reuters, AP).
  - House Democrats nominate Hakeem Jeffries for Speaker, 251-11: the first
    Black nominee; the full House votes Jan 3, 2027, needs 218 (Al Jazeera,
    NPR, AP).
  - Anthropic raises $81.3bn in the biggest IPO of all time, priced at $83
    a share (Al Jazeera).
  - Trump, Xi and Putin meet in Shenzhen on 19 Nov: the first-ever
    trilateral of the three nuclear powers; nuclear arms and the Iran war on
    the table, Ukraine is not; no agreement expected (China FM, Al Jazeera).
  - The Kerch Bridge is hit again, a second strike in two days on the link
    to Crimea.
  - Israel launches a ground operation in Gaza, with tanks advancing.
  - North Korea fires missiles in its latest weapons test.
  - Cyclone Akvan nears India, bringing heavy rain and strong winds.
  - The EU proposes a 45bn euro loan to keep Ukraine funded.
  - Ticker: Nvidia names an acting CEO; Fed sees more rate hikes.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (246, 241, 227)
INK = (22, 35, 63)
NAVY = (18, 30, 56)
NAVY_DARK = (12, 20, 40)
RED = (166, 28, 28)
GOLD = (192, 138, 30)
GOLD_LT = (224, 178, 74)
TEAL = (15, 95, 92)
BLUE = (43, 108, 176)
ORANGE = (214, 110, 30)
PINK = (255, 77, 157)
PINK_DK = (161, 30, 99)
CYAN = (25, 181, 201)
STONE = (216, 201, 163)
STONE_DK = (150, 132, 92)
WHITE = (250, 248, 242)
GREY = (110, 110, 100)


# ---------------------------------------------------------------- PNG output
def write_png(path, w, h, buf):
    """Write a truecolour PNG (filter 0 on every row). Deterministic."""
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw.extend(buf[y * w * 3:(y + 1) * w * 3])
    idat = zlib.compress(bytes(raw), 6)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", idat))
        f.write(chunk(b"IEND", b""))


# ------------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i] = c[0]
            self.buf[i + 1] = c[1]
            self.buf[i + 2] = c[2]

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.w, int(x + w))
        y1 = min(self.h, int(y + h))
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.buf[i] = c[0]
                self.buf[i + 1] = c[1]
                self.buf[i + 2] = c[2]

    def rect(self, x, y, w, h, c, t=1):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.px(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, c):
        cx, cy, r = int(cx), int(cy), int(r)
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy) <= r * r:
                    self.px(xx, yy, c)

    def ring(self, cx, cy, r, c, t=1):
        for a in range(360):
            rad = math.radians(a)
            for k in range(t):
                self.px(int(cx + (r + k) * math.cos(rad)),
                       int(cy + (r + k) * math.sin(rad)), c)

    def poly(self, pts, c):
        """Scanline fill of a polygon given as [(x, y), ...]."""
        if len(pts) < 3:
            return
        pts = [(float(x), float(y)) for x, y in pts]
        ymin = max(0, int(min(p[1] for p in pts)))
        ymax = min(self.h - 1, int(max(p[1] for p in pts)))
        n = len(pts)
        for y in range(ymin, ymax + 1):
            xs = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = max(0, int(math.ceil(xs[k])))
                xb = min(self.w - 1, int(math.floor(xs[k + 1])))
                for xx in range(xa, xb + 1):
                    self.px(xx, y, c)

    def poly_line(self, pts, c, close=True):
        n = len(pts)
        m = n if close else n - 1
        for i in range(m):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            self.line(x0, y0, x1, y1, c)


def shade(c, f):
    """Multiply an RGB colour by factor f (clamped)."""
    return (max(0, min(255, int(c[0] * f))),
            max(0, min(255, int(c[1] * f))),
            max(0, min(255, int(c[2] * f))))


def blend(a, b, t):
    """Linear blend of two RGB colours, t in [0, 1]."""
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


# ------------------------------------------------------------- bitmap font
# A 5x7 font, hand-designed for this page. Each glyph is 7 rows of 5 bits,
# most-significant bit = leftmost column. Only the characters the page uses.
FONT = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0x0C, 0x0C),
    ",": (0, 0, 0, 0, 0x0C, 0x04, 0x08),
    ":": (0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0),
    ";": (0, 0x0C, 0x0C, 0, 0x0C, 0x04, 0x08),
    "-": (0, 0, 0, 0x1F, 0, 0, 0),
    "'": (0x04, 0x04, 0x08, 0, 0, 0, 0),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04),
    "?": (0x0E, 0x11, 0x01, 0x02, 0x04, 0, 0x04),
    "/": (0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10),
    "%": (0x19, 0x19, 0x02, 0x04, 0x08, 0x13, 0x13),
    "$": (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "+": (0, 0x04, 0x04, 0x1F, 0x04, 0x04, 0),
    "=": (0, 0, 0x1F, 0, 0x1F, 0, 0),
    '"': (0x0A, 0x0A, 0, 0, 0, 0, 0),
    "*": (0, 0x04, 0x15, 0x0E, 0x15, 0x04, 0),
}


def text_w(s, scale):
    return len(s) * 6 * scale


def draw_text(cv, x, y, scale, color, s, bold=False):
    """Draw text with the bitmap font; returns the width in pixels."""
    cx = int(x)
    for ch in s:
        glyph = FONT.get(ch.upper(), FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits & (1 << (4 - col)):
                    cv.fill_rect(cx + col * scale, y + row * scale,
                                 scale, scale, color)
                    if bold:
                        cv.fill_rect(cx + col * scale + 1, y + row * scale,
                                     scale, scale, color)
        cx += 6 * scale
    return cx - int(x)


def draw_text_centre(cv, cx, y, scale, color, s, bold=False):
    w = text_w(s, scale)
    return draw_text(cv, cx - w // 2, y, scale, color, s, bold)


def wrap_text(s, max_w, scale):
    """Greedy word wrap; returns a list of lines fitting max_w pixels."""
    limit = max(1, max_w // (6 * scale))
    lines = []
    for chunk in s.split("\n"):
        words = chunk.split(" ")
        cur = ""
        for word in words:
            trial = (cur + " " + word).strip()
            if len(trial) <= limit:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines


def draw_para(cv, x, y, max_w, scale, color, s, leading=None):
    """Draw a wrapped paragraph; returns the y just below the last line."""
    if leading is None:
        leading = 7 * scale + 4
    lines = wrap_text(s, max_w, scale)
    yy = int(y)
    for line in lines:
        draw_text(cv, x, yy, scale, color, line)
        yy += leading
    return yy


# ------------------------------------------------------------- 3D helpers
# Points are (x, y, z) with +y up and +z toward the viewer. A face is a list
# of points plus a base colour; faces are shaded by their normal against a
# fixed light and painted far-to-near.

LIGHT = (0.45, 0.62, 0.64)


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vcross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vnorm(a):
    m = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) or 1.0
    return (a[0] / m, a[1] / m, a[2] / m)


def rot_y(p, ang):
    c, s = math.cos(ang), math.sin(ang)
    return (p[0] * c + p[2] * s, p[1], -p[0] * s + p[2] * c)


def rot_x(p, ang):
    c, s = math.cos(ang), math.sin(ang)
    return (p[0], p[1] * c - p[2] * s, p[1] * s + p[2] * c)


def project(p, cx, cy, scale, focal):
    """Perspective projection; returns (sx, sy, depth)."""
    f = focal / (focal + p[2])
    return (cx + p[0] * scale * f, cy - p[1] * scale * f, p[2])


def face_shade(pts, base):
    """Flat shade from the face normal against LIGHT; 0.45..1.15 range."""
    n = vnorm(vcross(vsub(pts[1], pts[0]), vsub(pts[2], pts[0])))
    d = vdot(n, vnorm(LIGHT))
    return shade(base, 0.55 + 0.6 * abs(d))


def draw_faces(cv, faces, cx, cy, scale, focal):
    """faces: list of (points, base_colour). Painter's algorithm."""
    items = []
    for pts, base in faces:
        if len(pts) < 3:
            continue
        depth = sum(p[2] for p in pts) / len(pts)
        items.append((depth, pts, base))
    items.sort(key=lambda t: t[0])
    for _, pts, base in items:
        proj = [project(p, cx, cy, scale, focal) for p in pts]
        cv.poly([(q[0], q[1]) for q in proj], face_shade(pts, base))


def extrude_poly(cv, pts2d, dx, dy, front, side, back, cx=0, cy=0):
    """Draw a 2D polygon extruded by (dx, dy): back, sides, then front."""
    back_pts = [(x + dx, y + dy) for x, y in pts2d]
    cv.poly(back_pts, back)
    n = len(pts2d)
    for i in range(n):
        x0, y0 = pts2d[i]
        x1, y1 = pts2d[(i + 1) % n]
        cv.poly([(x0, y0), (x1, y1), (x1 + dx, y1 + dy), (x0 + dx, y0 + dy)],
                side)
    cv.poly(pts2d, front)


def box3d_faces(x0, y0, z0, x1, y1, z1, c_top, c_front, c_side):
    """An axis-aligned box as faces: (top, front, left, right)."""
    a = (x0, y0, z0)
    b = (x1, y0, z0)
    c = (x1, y1, z0)
    d = (x0, y1, z0)
    a2 = (x0, y0, z1)
    b2 = (x1, y0, z1)
    c2 = (x1, y1, z1)
    d2 = (x0, y1, z1)
    return [
        ([d, c, c2, d2], c_top),      # top
        ([a, b, b2, a2], c_front),    # front
        ([a, a2, d2, d], c_side),     # left
        ([b, c, c2, b2], c_side),     # right
    ]


# -------------------------------------------------------------------- globe
def latlon_point(lat, lon):
    """Unit-sphere point for latitude/longitude in degrees."""
    la = math.radians(lat)
    lo = math.radians(lon)
    return (math.cos(la) * math.sin(lo), math.sin(la), math.cos(la) * math.cos(lo))


def draw_globe(cv, cx, cy, r, spin_deg, tilt_deg, pins):
    """Shaded sphere with graticule lines and glowing pins.

    pins: list of (lat, lon, colour, label). Only front-facing pins draw.
    Returns the projected pin positions for the legend (unused by caller).
    """
    spin = math.radians(spin_deg)
    tilt = math.radians(tilt_deg)
    ocean = (31, 78, 121)
    ocean_dk = (20, 52, 84)
    grid_c = (148, 178, 205)

    def xform(p):
        return rot_x(rot_y(p, spin), tilt)

    # Ocean quads, 15-degree cells, painter-sorted by depth.
    faces = []
    step = 15
    for la in range(-90, 90, step):
        for lo in range(-180, 180, step):
            corners = [latlon_point(la, lo), latlon_point(la, lo + step),
                       latlon_point(la + step, lo + step),
                       latlon_point(la + step, lo)]
            moved = [xform(p) for p in corners]
            if sum(p[2] for p in moved) / 4.0 <= -0.15:
                continue
            faces.append((moved, ocean))
    # Scale sphere points to radius r and paint.
    scaled = []
    for pts, base in faces:
        scaled.append(([(p[0] * r, p[1] * r, p[2] * r) for p in pts], base))
    draw_faces(cv, scaled, cx, cy, 1.0, 900.0)

    # Graticule: latitude and longitude lines, front hemisphere only.
    for la in range(-60, 61, 30):
        pts = []
        for lo in range(-180, 181, 6):
            p = xform(latlon_point(la, lo))
            if p[2] > -0.05:
                sx, sy, _ = project((p[0] * r, p[1] * r, p[2] * r),
                                    cx, cy, 1.0, 900.0)
                pts.append((sx, sy))
        for i in range(len(pts) - 1):
            cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                    grid_c)
    for lo in range(-180, 180, 30):
        pts = []
        for la in range(-90, 91, 6):
            p = xform(latlon_point(la, lo))
            if p[2] > -0.05:
                sx, sy, _ = project((p[0] * r, p[1] * r, p[2] * r),
                                    cx, cy, 1.0, 900.0)
                pts.append((sx, sy))
        for i in range(len(pts) - 1):
            cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                    grid_c)

    # Rim.
    cv.ring(cx, cy, r, NAVY, 2)
    # Glowing pins.
    for lat, lon, col, _label in pins:
        p = xform(latlon_point(lat, lon))
        if p[2] <= 0.03:
            continue
        sx, sy, _ = project((p[0] * r, p[1] * r, p[2] * r), cx, cy, 1.0,
                            900.0)
        cv.disc(sx, sy, 11, blend(col, PAPER, 0.75))
        cv.disc(sx, sy, 7, blend(col, PAPER, 0.45))
        cv.disc(sx, sy, 4, col)
        cv.disc(sx, sy, 2, WHITE)


# ------------------------------------------------------------ scene pieces
def v_letter_pts(x, y, w, h):
    """A block letter V as a polygon in a w x h box at (x, y)."""
    return [(x, y), (x + 0.30 * w, y), (x + 0.50 * w, y + 0.63 * h),
            (x + 0.70 * w, y), (x + w, y), (x + 0.69 * w, y + h),
            (x + 0.31 * w, y + h)]


def i_letter_pts(x, y, w, h):
    """A block letter I with serifs as a polygon in a w x h box."""
    return [(x, y), (x + w, y), (x + w, y + 0.16 * h),
            (x + 0.66 * w, y + 0.16 * h), (x + 0.66 * w, y + 0.84 * h),
            (x + w, y + 0.84 * h), (x + w, y + h), (x, y + h),
            (x, y + 0.84 * h), (x + 0.34 * w, y + 0.84 * h),
            (x + 0.34 * w, y + 0.16 * h), (x, y + 0.16 * h)]


def draw_skyline(cv, x0, y_base, x1, color, win, heights=None):
    """Neon building silhouettes along y_base, deterministic heights."""
    if heights is None:
        heights = [26, 44, 34, 58, 40, 66, 30, 50, 38, 62, 28, 46, 36, 54]
    bw = 22
    gap = 10
    x = x0
    i = 0
    while x + bw <= x1:
        h = heights[i % len(heights)]
        cv.fill_rect(x, y_base - h, bw, h, color)
        # Lit windows: two gold dots per building.
        cv.fill_rect(x + 5, y_base - h + 8, 3, 3, win)
        cv.fill_rect(x + 13, y_base - h + 18, 3, 3, win)
        x += bw + gap
        i += 1


def draw_capitol(cv, x0, y0, w, h):
    """A 3D Capitol dome with columns, inside a w x h box at (x0, y0)."""
    cx = x0 + w // 2
    base_y = y0 + h - 6
    drum_top = base_y - 20
    rx = min(52, w // 2 - 8)
    rise = 22
    # Dome: true half-ellipse rising above the drum, extruded up-right.
    dome = []
    for a in range(0, 181, 9):
        rad = math.radians(a)
        dome.append((cx + rx * math.cos(rad), drum_top - rise * math.sin(rad)))
    dome.append((cx - rx, drum_top))
    extrude_poly(cv, dome, 7, -5, STONE, STONE_DK, shade(STONE_DK, 0.6))
    # Lantern on top of the dome.
    cv.fill_rect(cx - 4, drum_top - rise - 6, 8, 6, STONE_DK)
    cv.disc(cx, drum_top - rise - 7, 2, GOLD)
    # Drum + columns.
    cv.fill_rect(cx - rx, drum_top, 2 * rx, 6, STONE_DK)
    for k in range(5):
        col_x = cx - rx + 6 + k * ((2 * rx - 20) // 4)
        cv.fill_rect(col_x, drum_top + 6, 7, base_y - drum_top - 8, STONE)
        cv.fill_rect(col_x - 1, drum_top + 6, 9, 3, STONE_DK)
    cv.fill_rect(cx - rx - 2, base_y - 2, 2 * rx + 4, 5, STONE_DK)


def draw_ipo_bars(cv, x0, y0, w, h):
    """Three rising 3D bars, the tallest marked 81.3 on it."""
    base_y = y0 + h - 6
    bars = [(TEAL, 16), (GOLD, 26), (RED, 34)]
    bw = 44
    gap = 14
    x = x0 + (w - (3 * bw + 2 * gap)) // 2
    for col, bh in bars:
        extrude_poly(cv, [(x, base_y - bh), (x + bw, base_y - bh),
                          (x + bw, base_y), (x, base_y)],
                     9, -7, col, shade(col, 0.6), shade(col, 0.4))
        x += bw + gap
    # Value label in white on the tallest bar, centred on it.
    tx = x0 + (w - (3 * bw + 2 * gap)) // 2 + 2 * (bw + gap)
    draw_text_centre(cv, tx + bw // 2, base_y - 34 + 10, 2, WHITE, "81.3",
                     bold=True)
    draw_text(cv, x0 + 4, base_y - 10, 1, GREY, "$BN")


def draw_summit_table(cv, x0, y0, w, h):
    """A round summit table with three chairs in three colours."""
    cx = x0 + w // 2
    cy = y0 + h - 24
    # Table top: ellipse approximated by a 24-gon, extruded downward.
    top = []
    for a in range(0, 360, 15):
        rad = math.radians(a)
        top.append((cx + 88 * math.cos(rad), cy + 13 * math.sin(rad)))
    extrude_poly(cv, top, 0, 10, GOLD_LT, shade(GOLD, 0.55),
                 shade(GOLD, 0.35))
    # Pedestal.
    cv.fill_rect(cx - 7, cy + 10, 14, 12, STONE_DK)
    # Three chairs: extruded seats with a coloured head above each.
    chairs = [(cx - 80, RED), (cx - 13, BLUE), (cx + 54, TEAL)]
    for ch_x, col in chairs:
        extrude_poly(cv, [(ch_x, cy - 22), (ch_x + 26, cy - 22),
                          (ch_x + 26, cy - 8), (ch_x, cy - 8)],
                     5, -4, col, shade(col, 0.6), shade(col, 0.4))
        cv.disc(ch_x + 13, cy - 30, 5, col)
        cv.disc(ch_x + 13, cy - 30, 2, WHITE)


def draw_bridge(cv, x0, y0, w, h):
    """The Kerch Bridge: deck with a collapsed middle span, smoke rising."""
    base_y = y0 + h - 8
    # Water strip.
    cv.fill_rect(x0, base_y, w, 8, (31, 78, 121))
    cv.line(x0 + 8, base_y + 3, x0 + 60, base_y + 3, (148, 178, 205))
    cv.line(x0 + 130, base_y + 5, x0 + 200, base_y + 5, (148, 178, 205))
    deck_y = y0 + 20
    # Towers with cables.
    for tx in (x0 + 42, x0 + 158):
        cv.fill_rect(tx, y0 + 2, 5, deck_y - y0 + 4, STONE_DK)
        cv.line(tx + 2, y0 + 2, tx - 30, deck_y, STONE_DK)
        cv.line(tx + 2, y0 + 2, tx + 34, deck_y, STONE_DK)
    # Deck: left and right spans; the middle span has fallen into the gap.
    cv.fill_rect(x0, deck_y, 92, 6, STONE)
    cv.fill_rect(x0 + 123, deck_y, 92, 6, STONE)
    cv.poly([(x0 + 92, deck_y), (x0 + 108, deck_y + 2),
             (x0 + 104, deck_y + 12), (x0 + 94, deck_y + 10)], STONE_DK)
    cv.poly([(x0 + 123, deck_y), (x0 + 108, deck_y + 2),
             (x0 + 112, deck_y + 12), (x0 + 121, deck_y + 10)], STONE_DK)
    # Smoke plumes from the gap.
    cv.disc(x0 + 100, deck_y - 4, 5, GREY)
    cv.disc(x0 + 110, deck_y - 10, 6, blend(GREY, PAPER, 0.4))
    cv.disc(x0 + 104, deck_y - 17, 4, blend(GREY, PAPER, 0.6))


def draw_tanks(cv, x0, y0, w, h):
    """An armoured column advancing: two tanks with dust behind them."""
    ground_y = y0 + h - 8
    cv.fill_rect(x0, ground_y, w, 8, (206, 178, 130))
    for tx, s in ((x0 + 18, 1.0), (x0 + 118, 0.85)):
        hw = int(34 * s)
        hh = int(10 * s)
        hull_y = ground_y - hh
        extrude_poly(cv, [(tx, hull_y), (tx + hw, hull_y),
                          (tx + hw, ground_y), (tx, ground_y)],
                     4, -3, (74, 84, 66), shade((74, 84, 66), 0.6),
                     shade((74, 84, 66), 0.4))
        tw = int(16 * s)
        th = int(8 * s)
        tur_y = hull_y - th
        extrude_poly(cv, [(tx + 8, tur_y), (tx + 8 + tw, tur_y),
                          (tx + 8 + tw, hull_y), (tx + 8, hull_y)],
                     3, -2, (92, 102, 82), shade((92, 102, 82), 0.6),
                     shade((92, 102, 82), 0.4))
        cv.line(tx + 8 + tw, tur_y + th // 2, tx + hw + 16,
                tur_y + th // 2, (40, 44, 38))
        for k in range(3):
            cv.disc(tx + 7 + k * 11, ground_y + 1, 2, (40, 44, 38))
        cv.disc(tx - 4, hull_y + 2, 4, blend((206, 178, 130), PAPER, 0.3))
        cv.disc(tx - 10, hull_y - 2, 3, blend((206, 178, 130), PAPER, 0.5))


def draw_missile(cv, x0, y0, w, h):
    """A missile lifting off its pad, flame and smoke below it."""
    base_y = y0 + h - 6
    # Launch pad.
    cv.fill_rect(x0 + 20, base_y - 4, 44, 4, STONE_DK)
    # Flame: orange outer, yellow inner, smoke puffs.
    cv.poly([(x0 + 38, base_y - 10), (x0 + 54, base_y - 10),
             (x0 + 46, base_y + 2)], ORANGE)
    cv.poly([(x0 + 41, base_y - 10), (x0 + 51, base_y - 10),
             (x0 + 46, base_y - 4)], GOLD_LT)
    cv.disc(x0 + 30, base_y - 2, 5, GREY)
    cv.disc(x0 + 62, base_y - 1, 4, blend(GREY, PAPER, 0.4))
    # Rocket body, extruded, with nose cone and fins.
    extrude_poly(cv, [(x0 + 38, y0 + 12), (x0 + 54, y0 + 12),
                      (x0 + 54, base_y - 10), (x0 + 38, base_y - 10)],
                 4, -3, WHITE, shade(WHITE, 0.75), shade(WHITE, 0.55))
    cv.poly([(x0 + 38, y0 + 12), (x0 + 54, y0 + 12), (x0 + 46, y0 + 1)],
            RED)
    cv.poly([(x0 + 38, base_y - 16), (x0 + 32, base_y - 6),
             (x0 + 38, base_y - 6)], RED)
    cv.poly([(x0 + 54, base_y - 16), (x0 + 60, base_y - 6),
             (x0 + 54, base_y - 6)], RED)
    # A second, distant launch trail on the right.
    cv.line(x0 + 120, base_y - 2, x0 + 150, y0 + 8, blend(GREY, PAPER, 0.3))
    cv.disc(x0 + 150, y0 + 8, 3, RED)


def draw_cyclone(cv, x0, y0, w, h):
    """A cyclone spiral over the sea, with the coastline below."""
    cx = x0 + 78
    cy = y0 + 26
    # Sea.
    cv.fill_rect(x0, y0 + 34, w, h - 34, (31, 78, 121))
    # Storm disc, then spiral arms of growing radius.
    cv.disc(cx, cy, 26, WHITE)
    for k, r in enumerate((7, 12, 17, 22)):
        a0 = k * 55
        pts = []
        for a in range(a0, a0 + 250, 6):
            rad = math.radians(a)
            pts.append((cx + r * math.cos(rad), cy + r * math.sin(rad)))
        cv.poly_line(pts, TEAL, close=False)
    cv.disc(cx, cy, 4, WHITE)
    cv.ring(cx, cy, 5, TEAL, 1)
    # Coastline: land wedge at the bottom right.
    cv.poly([(x0 + 130, y0 + h), (x0 + 215, y0 + h), (x0 + 215, y0 + 36),
             (x0 + 170, y0 + 44), (x0 + 145, y0 + 52)], (206, 178, 130))
    # Rain streaks.
    for rx, ry in ((x0 + 20, y0 + 8), (x0 + 34, y0 + 16), (x0 + 130, y0 + 10),
                   (x0 + 150, y0 + 18), (x0 + 190, y0 + 6)):
        cv.line(rx, ry, rx - 3, ry + 7, (148, 178, 205))


def draw_eu(cv, x0, y0, w, h):
    """The EU flag beside rising stacks of gold coins."""
    cx = x0 + 52
    cy = y0 + 28
    # Flag: blue disc with a ring of twelve gold dots.
    cv.disc(cx, cy, 24, BLUE)
    cv.ring(cx, cy, 24, NAVY, 1)
    for k in range(12):
        rad = math.radians(k * 30)
        cv.disc(cx + int(16 * math.cos(rad)), cy + int(16 * math.sin(rad)),
                2, GOLD_LT)
    # Coin stacks of increasing height.
    base_y = y0 + h - 6
    for sx, n in ((x0 + 108, 2), (x0 + 138, 3), (x0 + 168, 4)):
        for k in range(n):
            extrude_poly(cv, [(sx, base_y - 5 * (k + 1)),
                              (sx + 20, base_y - 5 * (k + 1)),
                              (sx + 20, base_y - 5 * k),
                              (sx, base_y - 5 * k)],
                         3, -2, GOLD, shade(GOLD, 0.6), shade(GOLD, 0.4))


# ------------------------------------------------------------------ layout
def draw_scene(cv):
    cv.fill_rect(0, 0, W, H, PAPER)
    cv.rect(8, 8, W - 16, H - 16, NAVY, 2)
    cv.rect(14, 14, W - 28, H - 28, NAVY, 1)

    # Masthead.
    cv.fill_rect(20, 20, 984, 100, NAVY)
    draw_text_centre(cv, 512, 38, 5, WHITE, "THE WORLD IN ONE IMAGE", bold=True)
    draw_text_centre(cv, 512, 84, 2, GOLD_LT, "THURSDAY - 19 NOVEMBER 2026")
    cv.fill_rect(20, 124, 984, 4, GOLD)

    # Hero: globe on the left.
    draw_text(cv, 24, 140, 2, RED, "THE WORLD AT A GLANCE", bold=True)
    pins = [(25.8, -80.2, GOLD, "VICE CITY"),
            (38.9, -77.0, BLUE, "WASHINGTON"),
            (31.5, 34.5, ORANGE, "GAZA"),
            (45.3, 36.5, PINK, "KERCH")]
    draw_globe(cv, 246, 300, 140, 30, -15, pins)
    legend = [(GOLD, "VICE CITY"), (BLUE, "WASHINGTON"),
              (ORANGE, "GAZA"), (RED, "SHENZHEN*"), (PINK, "KERCH")]
    for i, (col, label) in enumerate(legend):
        lx = 36 + (i % 2) * 220
        ly = 452 + (i // 2) * 26
        cv.disc(lx, ly + 6, 5, col)
        draw_text(cv, lx + 12, ly, 2, INK, label)
    draw_text(cv, 36, 530, 1, GREY, "*SHENZHEN: SEE THE SUMMIT PANEL BELOW")
    cv.line(482, 136, 482, 560, NAVY)

    # Hero: lead story on the right.
    draw_text(cv, 496, 140, 2, RED, "GAMES - THE WAIT IS OVER", bold=True)
    draw_text(cv, 496, 168, 5, INK, "VICE CITY OPENS", bold=True)
    cv.fill_rect(496, 208, 504, 3, GOLD)
    draw_para(cv, 496, 224, 504, 2, INK,
              "AFTER 13 YEARS AND MORE THAN $1 BILLION, ROCKSTAR'S GRAND "
              "THEFT AUTO VI BEGINS ITS WORLDWIDE ROLLOUT AT MIDNIGHT, "
              "STARTING IN NEW ZEALAND. EARLY REVIEWS GIVE IT 99 ON "
              "METACRITIC; PRE-SALES NEAR 16 MILLION COPIES.")
    draw_text(cv, 496, 344, 2, TEAL, "PS5 - XBOX SERIES X-S - $79.99 - $99.99",
              bold=True)

    # Neon VI panel.
    cv.fill_rect(496, 360, 504, 200, NAVY_DARK)
    draw_skyline(cv, 512, 552, 984, shade(CYAN, 0.45), GOLD_LT,
                 heights=[14, 20, 16, 26, 18, 24, 15, 22, 17, 25, 14, 21,
                          16, 23])
    extrude_poly(cv, v_letter_pts(628, 388, 140, 116), 14, -12,
                 PINK, PINK_DK, shade(PINK_DK, 0.6))
    extrude_poly(cv, i_letter_pts(798, 388, 70, 116), 14, -12,
                 CYAN, shade(CYAN, 0.55), shade(CYAN, 0.35))
    draw_text_centre(cv, 748, 510, 2, GOLD_LT,
                     "LUCIA AND JASON RETURN TO LEONIDA")

    # Bottom grid: two rows of four story panels.
    panels_a = [
        (20, "WASHINGTON", "FIRST TO GAVEL",
         "HOUSE DEMOCRATS NOMINATE HAKEEM JEFFRIES FOR SPEAKER, 251-11 - "
         "FIRST BLACK NOMINEE. VOTE JAN. 3.",
         draw_capitol),
        (271, "WALL STREET", "THE $81.3BN DEBUT",
         "ANTHROPIC RAISES $81.3 BILLION IN THE BIGGEST IPO EVER, "
         "PRICED AT $83 A SHARE.",
         draw_ipo_bars),
        (522, "SHENZHEN", "THREE AT TABLE",
         "TRUMP, XI AND PUTIN MEET FOR THE FIRST TIME - NUCLEAR ARMS AND "
         "IRAN ON THE TABLE. UKRAINE IS NOT.",
         draw_summit_table),
        (773, "KERCH STRAIT", "BRIDGE HIT AGAIN",
         "THE KERCH BRIDGE IS HIT AGAIN - A SECOND STRIKE IN TWO DAYS ON "
         "THE LINK TO CRIMEA.",
         draw_bridge),
    ]
    panels_b = [
        (20, "GAZA", "GROUND OPERATION",
         "ISRAEL LAUNCHES A GROUND OPERATION IN GAZA, WITH TANKS "
         "ADVANCING INTO THE STRIP.",
         draw_tanks),
        (271, "NORTH KOREA", "MISSILES FIRED",
         "NORTH KOREA FIRES MISSILES IN ITS LATEST WEAPONS TEST.",
         draw_missile),
        (522, "BAY OF BENGAL", "STORM NEARS INDIA",
         "CYCLONE AKVAN NEARS INDIA, BRINGING HEAVY RAIN AND STRONG "
         "WINDS TO THE COAST.",
         draw_cyclone),
        (773, "BRUSSELS", "EU'S 45BN LOAN",
         "THE EU PROPOSES A 45 BILLION EURO LOAN TO KEEP UKRAINE FUNDED.",
         draw_eu),
    ]
    for y0, panels in ((572, panels_a), (744, panels_b)):
        for x0, kicker, headline, body, art in panels:
            cv.rect(x0, y0, 231, 164, NAVY, 1)
            draw_text(cv, x0 + 10, y0 + 10, 2, RED, kicker, bold=True)
            draw_text(cv, x0 + 10, y0 + 30, 2, INK, headline, bold=True)
            cv.fill_rect(x0 + 10, y0 + 50, 211, 2, GOLD)
            art(cv, x0 + 8, y0 + 56, 215, 56)
            draw_para(cv, x0 + 10, y0 + 118, 211, 1, INK, body)

    # Ticker.
    cv.fill_rect(20, 916, 984, 34, NAVY)
    draw_text(cv, 28, 924, 2, GOLD_LT,
              "NVIDIA NAMES AN ACTING CEO * FED SEES MORE RATE HIKES *",
              bold=True)

    # Footer.
    draw_text_centre(cv, 512, 960, 2, INK,
                     "THE WORLD IN ONE IMAGE - 19 NOVEMBER 2026", bold=True)
    draw_text_centre(cv, 512, 982, 1, GREY,
                     "DRAWN BY A PROGRAM - NO PHOTOGRAPH - MAKE.FUN")


# --------------------------------------------------------------------- main
def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = Canvas(W, H, PAPER)
    draw_scene(cv)
    path = os.path.join(out_dir, "entry.png")
    write_png(path, W, H, cv.buf)
    print("wrote " + path)


if __name__ == "__main__":
    main()
