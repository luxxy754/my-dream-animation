"""DUNIYA: har location, prop aur effect yahin FIXED tareeqe se bante hain (koi random nahi => har video mein bilkul same).

STYLE BIBLE (isse mat badlo, warna videos ka look badal jayega):
  - Canvas 1920x1080, zameen (pairon ki line) y=GROUND=940. Outline rang OUT, moti line OW=4px. Flat rang + halka gradient.
  - Har location ki cheezein neeche LOCATIONS mein likhi hain; Gemini sirf in mein se chunta hai, naya kuch nahi banata.
  - "random" jaisa kuch bhi random.Random(seed) se aata hai (seed har location ka fixed) => hamesha wahi jagah.
Naya location jodna ho: ek draw_<naam>(c) function likho aur LOCATIONS + DRAWERS mein naam daal do.
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, GROUND = 1920, 1080, 940
S = 2  # supersample
OUT = (34, 30, 48)
OW = 4
FONT_BOLD = next((p for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                              "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"] if os.path.exists(p)), None)

LOCATIONS = {
    "room": "Shazy's bedroom: bed with red blanket on the left, window with daylight, SZ wolf poster, wall clock, desk on the right with a PC monitor showing green code, skateboard hanging on the wall, bookshelf, red rug, wooden floor",
    "classroom": "school classroom: big green blackboard with chalk writing, wall clock, window with blue sky, teacher's desk, student desks at the back, tiled floor",
    "street": "sunny city street: row of colourful buildings, a shop with striped awning and SHOP sign, sidewalk, road with dashed line, lamp posts, trees",
    "park": "sunny park: green hills, trees, wooden bench, sandy path, bushes with flowers, a lamp post, fountain",
    "cafe": "cosy cafe: counter with coffee machine, menu board, three hanging lamps, window, tables with stools, black-white checker floor",
    "rooftop": "building rooftop at sunset: orange-purple sky, big sun, city skyline, water tank, antenna, concrete parapet, string lights",
    "skatepark": "skatepark: graffiti wall with SZ tag, quarter-pipe ramp, fun box, metal rail, traffic cones, chain fence, grey concrete floor",
    "living_room": "family living room: brown sofa, TV on a stand, window with curtains, framed pictures, plant, floor lamp, carpet",
    "market": "busy bazaar: fruit stalls with red-white and green-white awnings, crates of oranges apples bananas, hanging flags, FRESH sign, stone ground",
    "night_street": "street at night: dark blue sky, moon and stars, dark buildings with warm lit windows, glowing lamp posts, dark road",
}


# ------------------------------------------------------------------ canvas helpers
class Cv:
    def __init__(self, w=W, h=H, bg=(255, 255, 255)):
        self.w, self.h = w, h
        self.im = Image.new("RGBA" if bg is None else "RGB", (w * S, h * S), (0, 0, 0, 0) if bg is None else bg)
        self.d = ImageDraw.Draw(self.im)

    def P(self, pts):
        return [(x * S, y * S) for x, y in pts]

    def rect(self, x0, y0, x1, y1, fill=None, out=OUT, w=OW, r=0):
        box = (x0 * S, y0 * S, x1 * S, y1 * S)
        if r:
            self.d.rounded_rectangle(box, r * S, fill=fill, outline=out, width=w * S if out else 0)
        else:
            self.d.rectangle(box, fill=fill, outline=out, width=w * S if out else 0)

    def ell(self, x0, y0, x1, y1, fill=None, out=OUT, w=OW):
        self.d.ellipse((x0 * S, y0 * S, x1 * S, y1 * S), fill=fill, outline=out, width=w * S if out else 0)

    def circ(self, x, y, r, fill=None, out=OUT, w=OW):
        self.ell(x - r, y - r, x + r, y + r, fill, out, w)

    def poly(self, pts, fill=None, out=OUT, w=OW):
        p = self.P(pts)
        if fill:
            self.d.polygon(p, fill=fill)
        if out:
            self.d.line(p + [p[0]], fill=out, width=w * S, joint="curve")

    def line(self, pts, col=OUT, w=OW):
        self.d.line(self.P(pts), fill=col, width=w * S, joint="curve")

    def text(self, x, y, s, size, fill=(255, 255, 255), out=None, anchor="mm"):
        f = ImageFont.truetype(FONT_BOLD, size * S) if FONT_BOLD else ImageFont.load_default()
        self.d.text((x * S, y * S), s, font=f, fill=fill, anchor=anchor,
                    stroke_width=(3 * S if out else 0), stroke_fill=out)

    def grad(self, y0, y1, top, bot, x0=0, x1=None):
        x1 = self.w if x1 is None else x1
        n = max(1, int((y1 - y0) * S))
        t = np.linspace(0, 1, n)[:, None]
        col = (np.array(top)[None, :] * (1 - t) + np.array(bot)[None, :] * t).astype(np.uint8)
        arr = np.repeat(col[:, None, :], int((x1 - x0) * S), axis=1)
        self.im.paste(Image.fromarray(arr, "RGB"), (int(x0 * S), int(y0 * S)))

    def overlay(self, fn, alpha):
        """fn(canvas) se alag layer bana kar alpha ke saath milao (glow / shadow)."""
        lay = Cv(self.w, self.h, None)
        fn(lay)
        a = np.array(lay.im)
        a[..., 3] = (a[..., 3] * alpha).astype(np.uint8)
        base = self.im.convert("RGBA")
        base.alpha_composite(Image.fromarray(a, "RGBA"))
        self.im = base.convert("RGB")
        self.d = ImageDraw.Draw(self.im)

    def result(self, rgba=False):
        im = self.im.resize((self.w, self.h), Image.LANCZOS)
        a = np.array(im)
        if rgba:
            return a[..., [2, 1, 0, 3]].copy()
        return a[..., ::-1].copy()  # BGR


def shade(col, f):
    return tuple(max(0, min(255, int(v * f))) for v in col)


def cloud(c, x, y, s=1.0, fill=(255, 255, 255)):
    for dx, dy, r in [(-60, 10, 44), (-10, -14, 58), (50, 6, 48), (100, 18, 34)]:
        c.circ(x + dx * s, y + dy * s, r * s, fill, None)
    c.rect(x - 105 * s, y + 10 * s, x + 128 * s, y + 52 * s, fill, None)


def tree(c, x, g, s=1.0, leaf=(92, 170, 84)):
    c.rect(x - 16 * s, g - 150 * s, x + 16 * s, g, (140, 98, 62), r=4)
    for dx, dy, r in [(-60, -190, 80), (60, -190, 80), (0, -250, 92), (0, -170, 90)]:
        c.circ(x + dx * s, g + dy * s, r * s, leaf)
    for dx, dy, r in [(-30, -230, 14), (40, -190, 12), (-50, -170, 10)]:
        c.circ(x + dx * s, g + dy * s, r * s, shade(leaf, 1.18), None)


def lamp_post(c, x, g, lit=False):
    c.rect(x - 9, g - 360, x + 9, g, (70, 74, 90), r=3)
    c.rect(x - 38, g - 392, x + 38, g - 360, (70, 74, 90), r=8)
    c.rect(x - 30, g - 360, x + 30, g - 346, (255, 232, 140) if lit else (210, 214, 224), None)


def building(c, x, y, w, h, col, rows, cols, lit=0.0, rnd=None, win=(188, 222, 248)):
    c.rect(x, y, x + w, y + h, col)
    c.rect(x - 6, y - 14, x + w + 6, y + 6, shade(col, 0.82))
    mx, my = w / (cols * 2 + 1), h / (rows * 2 + 1.4)
    for r in range(rows):
        for k in range(cols):
            on = rnd is not None and rnd.random() < lit
            c.rect(x + mx * (1 + 2 * k), y + my * (1 + 2 * r) + 6, x + mx * (2 + 2 * k), y + my * (2 + 2 * r) + 6,
                   (255, 220, 120) if on else win, w=3)


def window(c, x, y, w, h, sky=((140, 200, 250), (215, 238, 255)), night=False):
    c.grad(y, y + h, *( ((20, 30, 70), (50, 60, 110)) if night else sky), x0=x, x1=x + w)
    if not night:
        cloud(c, x + w * 0.35, y + h * 0.35, 0.35)
    c.rect(x, y, x + w, y + h, None, OUT, 8)
    c.line([(x + w / 2, y), (x + w / 2, y + h)], OUT, 6)
    c.line([(x, y + h / 2), (x + w, y + h / 2)], OUT, 6)
    c.rect(x - 14, y + h, x + w + 14, y + h + 16, (236, 226, 208), r=4)


def floor_planks(c, y0, col, line, step=150):
    c.grad(y0, H, col, shade(col, 0.82))
    c.line([(0, y0), (W, y0)], OUT, 5)
    for i, yy in enumerate([y0 + 55, y0 + 125, y0 + 215]):
        c.line([(0, yy), (W, yy)], line, 2)
    for r, yy in enumerate([y0, y0 + 55, y0 + 125]):
        for xx in range(-(r * 70) % step, W, step):
            c.line([(xx, yy), (xx, yy + (55 if r == 0 else 70 if r == 1 else 90))], line, 2)


def checker(c, y0, a, b, tile=120):
    c.rect(0, y0, W, H, a, None)
    for r in range(0, (H - y0) // tile + 1):
        for k in range(0, W // tile + 1):
            if (r + k) % 2:
                c.rect(k * tile, y0 + r * tile, (k + 1) * tile, y0 + (r + 1) * tile, b, None)
    c.line([(0, y0), (W, y0)], OUT, 5)


def shadow_row(c, y):
    c.overlay(lambda l: l.rect(0, y, W, y + 22, (0, 0, 0, 255), None), 0.12)


def stripes_awning(c, x0, x1, y, col1, col2, h=70, n=8):
    wdt = (x1 - x0) / n
    for i in range(n):
        c.poly([(x0 + i * wdt, y), (x0 + (i + 1) * wdt, y), (x0 + (i + 1) * wdt + 6, y + h), (x0 + i * wdt - 6, y + h)],
               col1 if i % 2 == 0 else col2, OUT, 3)
        c.circ(x0 + i * wdt + wdt / 2, y + h, wdt / 2, col1 if i % 2 == 0 else col2, OUT, 3)


# ------------------------------------------------------------------ locations
def draw_room(c, rnd):
    c.grad(0, 800, (186, 204, 238), (160, 180, 224))
    for xx in range(0, W, 120):
        c.rect(xx, 0, xx + 60, 800, (178, 197, 233), None)
    c.rect(0, 700, W, 800, (132, 152, 205), None)
    c.line([(0, 700), (W, 700)], OUT, 4)
    floor_planks(c, 800, (200, 154, 106), (150, 108, 70))
    c.ell(520, 880, 1400, 1040, (196, 70, 80), OUT, 5)
    c.ell(600, 905, 1320, 1015, (222, 108, 110), None)
    # bed
    c.rect(30, 560, 90, 830, (110, 74, 52), r=6)
    c.rect(60, 650, 560, 800, (120, 80, 56), r=10)
    c.rect(60, 590, 540, 700, (236, 236, 244), r=24)
    c.rect(60, 640, 540, 760, (204, 62, 70), r=18)
    c.rect(60, 690, 540, 718, (232, 120, 120), None)
    c.rect(80, 560, 230, 640, (250, 250, 255), r=26)
    c.rect(490, 790, 520, 830, (110, 74, 52), r=4)
    # shelf over the bed
    c.rect(90, 330, 500, 350, (150, 104, 66), r=4)
    for i, (col, hh) in enumerate([((220, 80, 80), 70), ((90, 150, 220), 86), ((240, 200, 80), 64), ((100, 190, 120), 78), ((170, 110, 200), 70)]):
        c.rect(110 + i * 34, 330 - hh, 140 + i * 34, 330, col, w=3)
    c.rect(330, 262, 440, 330, (250, 244, 230), r=6)
    c.line([(346, 285), (424, 285)], (120, 120, 140), 3)
    c.line([(346, 305), (404, 305)], (120, 120, 140), 3)
    # window + curtains
    window(c, 640, 150, 270, 320)
    c.poly([(600, 130), (700, 130), (680, 520), (600, 540)], (240, 150, 90))
    c.poly([(850, 130), (950, 130), (950, 540), (870, 520)], (240, 150, 90))
    c.rect(590, 118, 960, 140, (120, 84, 56), r=6)
    # SZ poster
    c.rect(1000, 180, 1170, 440, (46, 52, 70), r=8)
    c.rect(1016, 196, 1154, 424, (236, 236, 242), r=6)
    c.poly([(1040, 250), (1070, 215), (1100, 250), (1130, 215), (1130, 300), (1085, 330), (1040, 300)], (150, 154, 170))
    c.text(1085, 385, "SZ", 62, (40, 44, 60))
    # wall clock
    c.circ(1290, 160, 62, (250, 248, 240), OUT, 6)
    c.line([(1290, 160), (1290, 118)], OUT, 6)
    c.line([(1290, 160), (1322, 176)], OUT, 6)
    c.circ(1290, 160, 6, OUT, None)
    # skateboard on wall
    c.rect(1430, 250, 1820, 304, (234, 150, 60), r=26)
    c.rect(1470, 262, 1780, 292, (250, 210, 120), None, r=14)
    c.text(1625, 277, "SZ", 28, (90, 40, 20))
    for xx in (1490, 1760):
        c.rect(xx - 4, 304, xx + 26, 330, (80, 80, 96), r=4)
        c.circ(xx + 11, 340, 15, (240, 240, 245), OUT, 4)
    # desk + PC
    c.rect(1180, 640, 1870, 676, (172, 120, 78), r=6)
    c.rect(1210, 676, 1250, 930, (150, 104, 66), r=4)
    c.rect(1800, 676, 1840, 930, (150, 104, 66), r=4)
    c.rect(1560, 676, 1790, 760, (160, 112, 72), r=4)
    c.rect(1580, 690, 1770, 716, (190, 140, 96), r=4)
    c.rect(1330, 400, 1640, 600, (60, 64, 82), r=14)
    c.rect(1346, 416, 1624, 584, (22, 30, 38), r=8)
    for i, (xx, ww, col) in enumerate([(1366, 90, (80, 230, 140)), (1380, 140, (120, 200, 255)), (1380, 70, (80, 230, 140)),
                                       (1394, 120, (255, 200, 90)), (1366, 160, (80, 230, 140)), (1380, 100, (120, 200, 255)),
                                       (1394, 60, (80, 230, 140))]):
        c.rect(xx, 440 + i * 18, xx + ww, 450 + i * 18, col, None)
    c.rect(1462, 600, 1508, 640, (60, 64, 82), None)
    c.rect(1420, 630, 1550, 644, (60, 64, 82), r=5)
    c.rect(1330, 612, 1530, 640, (56, 58, 74), r=6)
    c.rect(1700, 520, 1790, 640, (70, 74, 94), r=8)
    c.circ(1745, 560, 10, (90, 230, 140), None)
    c.rect(1250, 592, 1300, 640, (240, 240, 245), r=8)
    # chair
    c.rect(1460, 700, 1620, 780, (60, 66, 100), r=18)
    c.rect(1515, 780, 1565, 900, (70, 70, 84), None)
    c.line([(1470, 912), (1610, 912)], OUT, 8)
    shadow_row(c, 930)


def draw_classroom(c, rnd):
    c.grad(0, 800, (244, 230, 196), (232, 214, 176))
    c.rect(0, 640, W, 800, (112, 160, 128), None)
    c.line([(0, 640), (W, 640)], OUT, 4)
    checker(c, 800, (218, 190, 148), (200, 168, 124), 100)
    c.rect(330, 120, 1180, 560, (136, 94, 60), r=10)
    c.rect(350, 140, 1160, 540, (44, 92, 76), r=6)
    c.text(520, 220, "2 + 2 = ?", 70, (240, 240, 235))
    c.text(560, 330, "PLEASE BE", 46, (210, 220, 215))
    c.text(520, 392, "QUIET!", 46, (210, 220, 215))
    c.line([(700, 470), (1100, 470)], (230, 230, 225), 4)
    for i in range(4):
        c.rect(700 + i * 28, 520, 722 + i * 28, 540, (245, 245, 240), None)
    c.rect(330, 540, 1180, 560, (160, 112, 72), r=4)
    c.circ(1290, 190, 66, (250, 248, 240), OUT, 6)
    c.line([(1290, 190), (1290, 142)], OUT, 6)
    c.line([(1290, 190), (1326, 206)], OUT, 6)
    window(c, 1440, 140, 340, 360)
    c.rect(70, 560, 260, 640, (240, 236, 220), r=6)
    c.text(165, 600, "RULES", 34, (150, 60, 60))
    # teacher desk
    c.rect(40, 700, 420, 740, (150, 104, 66), r=6)
    c.rect(60, 740, 400, 900, (172, 120, 78), r=4)
    c.rect(100, 650, 180, 700, (220, 70, 70), r=6)
    c.rect(220, 668, 320, 700, (250, 250, 245), r=4)
    # student desks
    for xx in (1330, 1580):
        c.rect(xx, 720, xx + 230, 750, (206, 160, 104), r=6)
        c.rect(xx + 20, 750, xx + 40, 880, (90, 94, 110), None)
        c.rect(xx + 190, 750, xx + 210, 880, (90, 94, 110), None)
        c.rect(xx + 60, 790, xx + 170, 830, (90, 120, 200), r=8)
    shadow_row(c, 930)


def draw_street(c, rnd):
    c.grad(0, 800, (150, 206, 250), (222, 242, 255))
    cloud(c, 300, 150, 1.1)
    cloud(c, 1300, 110, 0.9)
    cloud(c, 1740, 240, 0.7)
    cols = [(232, 160, 120), (130, 180, 214), (240, 206, 120), (170, 150, 200), (140, 200, 160), (236, 130, 130)]
    xs, k = 0, 0
    for w_, h_ in [(300, 480), (240, 560), (320, 440), (260, 520), (300, 600), (260, 460), (260, 540)]:
        building(c, xs, 800 - h_, w_, h_, cols[k % len(cols)], max(3, h_ // 130), 3, 0, rnd)
        xs += w_
        k += 1
    # shop
    c.rect(1180, 540, 1600, 800, (250, 236, 200))
    stripes_awning(c, 1150, 1630, 560, (220, 70, 70), (250, 245, 235), 80, 10)
    c.rect(1240, 690, 1330, 800, (120, 176, 220), w=4)
    c.rect(1400, 660, 1560, 800, (190, 226, 250), w=4)
    c.rect(1250, 490, 1530, 550, (60, 66, 90), r=10)
    c.text(1390, 520, "SHOP", 48, (255, 214, 90))
    # sidewalk + road
    c.rect(0, 780, W, 960, (206, 204, 196), None)
    c.rect(0, 780, W, 800, (176, 174, 168), None)
    c.line([(0, 780), (W, 780)], OUT, 4)
    for xx in range(0, W, 240):
        c.line([(xx, 800), (xx - 40, 960)], (178, 176, 170), 3)
    c.rect(0, 960, W, 990, (150, 148, 142), None)
    c.line([(0, 960), (W, 960)], OUT, 5)
    c.rect(0, 990, W, H, (86, 88, 100), None)
    for xx in range(40, W, 260):
        c.rect(xx, 1030, xx + 140, 1044, (246, 224, 120), None)
    lamp_post(c, 260, 800)
    lamp_post(c, 1730, 800)
    tree(c, 1000, 800, 0.8)


def draw_park(c, rnd):
    c.grad(0, 700, (146, 204, 250), (226, 244, 255))
    cloud(c, 420, 150, 1.0)
    cloud(c, 1500, 200, 1.2)
    c.circ(1700, 130, 70, (255, 232, 130), None)
    c.poly([(0, 560), (300, 430), (700, 520), (1100, 400), (1500, 500), (1920, 420), (1920, 800), (0, 800)], (150, 204, 130))
    c.poly([(0, 640), (400, 560), (900, 640), (1400, 560), (1920, 630), (1920, 800), (0, 800)], (118, 184, 100))
    for x in (200, 760, 1180, 1700):
        tree(c, x, 760, 0.9 if x % 2 else 1.1)
    c.rect(0, 760, W, H, (110, 182, 90), None)
    c.line([(0, 760), (W, 760)], OUT, 4)
    c.poly([(780, 760), (1140, 760), (1500, 1080), (420, 1080)], (232, 208, 150), OUT, 4)
    for i in range(26):
        x, y = 40 + rnd.random() * 1840, 790 + rnd.random() * 280
        c.line([(x, y), (x - 6, y - 22)], (80, 150, 70), 3)
    for x, y, col in [(300, 880, (250, 110, 130)), (330, 905, (250, 220, 90)), (1620, 860, (250, 250, 250)), (1650, 888, (250, 110, 130)), (140, 950, (250, 220, 90))]:
        c.circ(x, y, 12, col, OUT, 3)
        c.line([(x, y + 12), (x, y + 36)], (70, 140, 60), 3)
    # bench
    c.rect(1360, 700, 1760, 740, (170, 118, 74), r=6)
    c.rect(1360, 640, 1760, 676, (190, 136, 88), r=6)
    c.rect(1380, 740, 1404, 820, (70, 74, 90), None)
    c.rect(1716, 740, 1740, 820, (70, 74, 90), None)
    # fountain
    c.ell(180, 790, 520, 870, (200, 206, 216), OUT, 5)
    c.ell(210, 800, 490, 850, (130, 200, 240), None)
    c.rect(332, 650, 368, 820, (200, 206, 216), r=6)
    c.ell(270, 620, 430, 670, (200, 206, 216), OUT, 4)
    for dx in (-40, 0, 40):
        c.line([(350, 640), (350 + dx * 1.4, 700 + abs(dx))], (130, 200, 240), 5)
    lamp_post(c, 1180, 780)


def draw_cafe(c, rnd):
    c.grad(0, 800, (240, 208, 168), (226, 188, 146))
    c.rect(0, 600, W, 800, (170, 100, 76), None)
    for r in range(3):
        for k in range(24):
            c.rect(k * 90 + (45 if r % 2 else 0), 600 + r * 66, k * 90 + 88 + (45 if r % 2 else 0), 664 + r * 66, (186, 112, 86), None, w=2)
    c.line([(0, 600), (W, 600)], OUT, 4)
    checker(c, 800, (250, 246, 240), (60, 60, 74), 110)
    window(c, 120, 170, 400, 330, sky=((160, 210, 250), (236, 246, 255)))
    c.rect(100, 120, 540, 150, (150, 60, 60), r=6)
    for x, col in [(760, (240, 120, 90)), (1060, (250, 200, 90)), (1360, (110, 180, 230))]:
        c.line([(x, 0), (x, 150)], OUT, 4)
        c.poly([(x - 70, 230), (x + 70, 230), (x + 38, 150), (x - 38, 150)], col)
        c.ell(x - 28, 220, x + 28, 246, (255, 244, 190), None)
    # menu board
    c.rect(620, 270, 940, 520, (50, 56, 62), r=8)
    c.rect(636, 286, 924, 504, (36, 42, 48), None)
    c.text(780, 322, "MENU", 40, (255, 214, 120))
    for i, w_ in enumerate([200, 170, 210, 150]):
        c.rect(660, 364 + i * 36, 660 + w_, 372 + i * 36, (230, 230, 225), None)
        c.rect(860, 364 + i * 36, 896, 372 + i * 36, (255, 214, 120), None)
    # counter
    c.rect(1300, 560, 1920, 930, (120, 76, 56))
    c.rect(1280, 520, 1920, 570, (214, 164, 116), r=6)
    for k in range(5):
        c.rect(1330 + k * 118, 600, 1420 + k * 118, 900, (140, 92, 66), None, w=3)
    c.rect(1440, 380, 1640, 520, (200, 204, 216), r=12)
    c.rect(1470, 410, 1610, 470, (60, 66, 84), r=8)
    c.circ(1540, 440, 18, (250, 90, 80), None)
    c.rect(1700, 450, 1750, 520, (250, 250, 245), r=8)
    c.rect(1790, 430, 1890, 520, (236, 190, 120), r=10)
    # tables
    for x in (140, 460):
        c.ell(x - 120, 770, x + 120, 810, (190, 130, 90))
        c.rect(x - 12, 800, x + 12, 910, (90, 94, 110), None)
        c.line([(x - 70, 914), (x + 70, 914)], OUT, 8)
        c.rect(x + 160, 830, x + 230, 850, (206, 70, 80), r=8)
        c.rect(x + 190, 850, x + 200, 910, (90, 94, 110), None)
    shadow_row(c, 930)


def draw_rooftop(c, rnd):
    c.grad(0, 800, (255, 170, 90), (120, 80, 150))
    c.grad(0, 330, (90, 70, 150), (255, 160, 100))
    c.circ(960, 640, 230, (255, 226, 140), None)
    c.rect(0, 640, W, 800, (120, 80, 150), None)
    for x, y, w_ in [(140, 80, 7), (520, 150, 5), (1500, 100, 6), (1740, 190, 5), (880, 60, 4)]:
        c.circ(x, y, w_, (255, 250, 230), None)
    col = (66, 46, 104)
    xs = 0
    for w_, h_ in [(160, 330), (120, 440), (200, 260), (140, 520), (170, 380), (130, 300), (220, 470), (150, 340), (180, 420), (140, 280), (200, 360), (170, 250)]:
        c.rect(xs, 800 - h_, xs + w_, 800, col, None)
        for r in range(h_ // 70):
            for k in range(max(1, w_ // 50)):
                if rnd.random() < 0.4:
                    c.rect(xs + 12 + k * 44, 800 - h_ + 20 + r * 62, xs + 34 + k * 44, 800 - h_ + 44 + r * 62, (255, 214, 120), None)
        xs += w_
    # water tank + antenna
    c.rect(140, 540, 330, 640, (150, 110, 96), r=10)
    c.line([(160, 640), (150, 800)], OUT, 6)
    c.line([(310, 640), (320, 800)], OUT, 6)
    c.line([(1620, 800), (1620, 420)], OUT, 6)
    c.line([(1580, 480), (1660, 480)], OUT, 5)
    c.line([(1590, 530), (1650, 530)], OUT, 5)
    # parapet
    c.rect(0, 800, W, H, (170, 170, 184), None)
    c.rect(0, 780, W, 830, (206, 206, 218))
    for x in range(0, W, 200):
        c.line([(x, 830), (x, H)], (150, 150, 166), 3)
    c.line([(0, 830), (W, 830)], OUT, 4)
    # string lights
    pts = [(0, 300), (480, 380), (960, 330), (1440, 390), (1920, 310)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        c.line([(x0, y0), (x1, y1)], OUT, 3)
        for i in range(1, 6):
            x, y = x0 + (x1 - x0) * i / 6, y0 + (y1 - y0) * i / 6 + 14
            c.circ(x, y, 12, [(255, 214, 90), (255, 130, 130), (140, 220, 255)][i % 3], OUT, 3)


def draw_skatepark(c, rnd):
    c.grad(0, 700, (140, 200, 250), (214, 236, 255))
    cloud(c, 380, 140, 1.0)
    cloud(c, 1400, 190, 1.0)
    c.rect(0, 380, W, 800, (176, 180, 196), None)
    for sx, sy, ww, col in [(120, 430, 380, (250, 90, 110)), (560, 470, 300, (90, 200, 240)), (1000, 440, 360, (250, 214, 90)), (1420, 480, 400, (140, 220, 120))]:
        c.rect(sx, sy, sx + ww, sy + 130, col, r=40, w=0, out=None)
    c.text(940, 600, "SZ", 190, (255, 255, 255), OUT)
    c.line([(0, 380), (W, 380)], OUT, 5)
    for x in range(0, W, 120):
        c.line([(x, 190 + 190), (x + 60, 190 + 190)], OUT, 1)
    c.rect(0, 800, W, H, (190, 192, 202), None)
    c.line([(0, 800), (W, 800)], OUT, 4)
    for x in range(0, W, 220):
        c.line([(x, 800), (x - 80, H)], (170, 172, 184), 3)
    c.poly([(1440, 800), (1920, 800), (1920, 480), (1900, 590), (1840, 690), (1740, 760), (1600, 790)], (230, 130, 70), OUT, 5)
    c.poly([(220, 800), (300, 700), (640, 700), (720, 800)], (110, 170, 230), OUT, 5)
    c.rect(300, 690, 640, 712, (240, 240, 245), r=4)
    c.line([(900, 830), (1200, 830)], (220, 70, 70), 10)
    c.line([(930, 830), (930, 880)], OUT, 6)
    c.line([(1170, 830), (1170, 880)], OUT, 6)
    for x in (780, 1320):
        c.poly([(x - 30, 900), (x + 30, 900), (x + 12, 800), (x - 12, 800)], (250, 130, 50), OUT, 4)
        c.rect(x - 20, 840, x + 20, 858, (250, 250, 250), None)
    shadow_row(c, 930)


def draw_living_room(c, rnd):
    c.grad(0, 800, (238, 218, 186), (226, 200, 164))
    for xx in range(0, W, 100):
        c.rect(xx, 0, xx + 36, 800, (232, 208, 174), None)
    c.rect(0, 730, W, 800, (200, 150, 110), None)
    c.line([(0, 730), (W, 730)], OUT, 4)
    floor_planks(c, 800, (176, 124, 84), (130, 90, 60))
    c.ell(300, 870, 1600, 1060, (96, 150, 170), OUT, 5)
    c.ell(380, 895, 1520, 1030, (126, 182, 200), None)
    window(c, 80, 150, 300, 380)
    c.poly([(40, 120), (140, 120), (120, 600), (40, 620)], (200, 80, 90))
    c.poly([(330, 120), (430, 120), (430, 620), (350, 600)], (200, 80, 90))
    for x, y, w_, h_ in [(520, 200, 150, 190), (710, 180, 200, 140), (960, 230, 130, 170)]:
        c.rect(x, y, x + w_, y + h_, (150, 104, 66), r=4)
        c.rect(x + 14, y + 14, x + w_ - 14, y + h_ - 14, (200, 226, 244), None)
        c.circ(x + w_ / 2, y + h_ / 2 - 12, 22, (240, 190, 150), OUT, 3)
        c.rect(x + w_ / 2 - 28, y + h_ / 2 + 12, x + w_ / 2 + 28, y + h_ - 22, (120, 150, 210), None)
    # sofa
    c.rect(430, 600, 1130, 820, (156, 92, 66), r=30)
    c.rect(400, 680, 500, 860, (172, 104, 74), r=24)
    c.rect(1060, 680, 1160, 860, (172, 104, 74), r=24)
    c.rect(500, 730, 1060, 830, (190, 120, 88), r=18)
    c.rect(560, 640, 680, 730, (240, 190, 90), r=14)
    c.rect(450, 850, 480, 900, OUT, None)
    c.rect(1110, 850, 1140, 900, OUT, None)
    # TV
    c.rect(1330, 740, 1830, 790, (110, 76, 56), r=6)
    c.rect(1360, 790, 1400, 900, (96, 66, 48), None)
    c.rect(1760, 790, 1800, 900, (96, 66, 48), None)
    c.rect(1380, 440, 1790, 720, (40, 44, 56), r=14)
    c.rect(1396, 456, 1774, 704, (90, 160, 220), r=8)
    c.poly([(1396, 650), (1500, 560), (1600, 640), (1680, 590), (1774, 660), (1774, 704), (1396, 704)], (110, 190, 130), None)
    c.circ(1690, 520, 26, (255, 230, 120), None)
    # lamp + plant
    c.rect(1218, 380, 1230, 900, OUT, None)
    c.poly([(1170, 380), (1280, 380), (1250, 300), (1200, 300)], (255, 226, 150))
    c.ell(1186, 880, 1262, 910, (70, 74, 90), None)
    c.rect(1860, 700, 1920, 800, (210, 110, 70), r=6)
    for dx, ang in [(-40, -30), (0, 0), (40, 30)]:
        c.poly([(1890, 700), (1890 + dx * 1.6, 600), (1894 + dx * 0.5, 700)], (80, 170, 100), OUT, 3)
    shadow_row(c, 930)


def draw_market(c, rnd):
    c.grad(0, 800, (150, 206, 250), (230, 244, 255))
    cloud(c, 440, 130, 0.9)
    cloud(c, 1480, 100, 1.0)
    for i, (x, h_, col) in enumerate([(0, 520, (232, 170, 130)), (330, 600, (200, 160, 210)), (700, 480, (240, 214, 130)),
                                      (1060, 580, (150, 200, 170)), (1420, 500, (238, 150, 140)), (1740, 560, (140, 190, 220))]):
        building(c, x, 780 - h_, 340, h_, col, 3, 3, 0, rnd)
    # flags
    c.line([(0, 200), (960, 270), (1920, 200)], OUT, 3)
    for i in range(1, 22):
        x = i * 87
        y = 200 + 70 * math.sin(math.pi * (x / 1920)) * 0.9 if False else 200 + (70 * (1 - abs(x - 960) / 960))
        c.poly([(x - 18, y), (x + 18, y), (x, y + 44)], [(230, 80, 90), (250, 214, 90), (90, 190, 130), (100, 160, 230)][i % 4], OUT, 2)
    c.rect(0, 780, W, H, (196, 176, 146), None)
    c.line([(0, 780), (W, 780)], OUT, 4)
    for r in range(4):
        for k in range(14):
            c.rect(k * 150 + (75 if r % 2 else 0), 780 + r * 80, k * 150 + 148 + (75 if r % 2 else 0), 856 + r * 80, (186, 164, 134), None, w=2)
    # stalls
    stripes_awning(c, 60, 700, 440, (222, 70, 70), (250, 244, 232), 90, 10)
    c.rect(60, 530, 700, 790, (170, 118, 74))
    c.rect(1180, 440, 1860, 450, OUT, None)
    stripes_awning(c, 1180, 1860, 440, (70, 170, 110), (250, 244, 232), 90, 10)
    c.rect(1180, 530, 1860, 790, (170, 118, 74))
    c.rect(300, 350, 480, 420, (60, 66, 90), r=10)
    c.text(390, 385, "FRESH", 40, (255, 214, 90))
    for x0, x1, kinds in [(90, 670, [(250, 150, 40), (220, 50, 60), (250, 220, 70)]), (1210, 1830, [(220, 50, 60), (250, 150, 40), (130, 200, 70)])]:
        c.rect(x0, 640, x1, 760, (200, 150, 96), r=6)
        n = int((x1 - x0) / 56)
        for r in range(2):
            for k in range(n):
                c.circ(x0 + 30 + k * 56 + (28 if r else 0) * 0, 628 - r * 40, 26, kinds[(k + r) % 3], OUT, 3)
    shadow_row(c, 930)


def draw_night_street(c, rnd):
    c.grad(0, 800, (14, 18, 52), (40, 44, 96))
    for i in range(46):
        c.circ(30 + rnd.random() * 1860, 20 + rnd.random() * 420, 2 + rnd.random() * 2.6, (255, 250, 230), None)
    c.circ(1560, 170, 96, (250, 244, 214), None)
    c.circ(1530, 150, 24, (226, 220, 190), None)
    c.circ(1600, 200, 16, (226, 220, 190), None)
    cols = [(34, 40, 82), (42, 48, 94), (30, 36, 72)]
    xs, k = 0, 0
    for w_, h_ in [(300, 520), (260, 620), (320, 460), (260, 560), (300, 650), (280, 480), (260, 580)]:
        building(c, xs, 800 - h_, w_, h_, cols[k % 3], max(3, h_ // 130), 3, 0.5, rnd, (70, 80, 130))
        xs += w_
        k += 1
    c.rect(0, 780, W, 960, (70, 72, 98), None)
    c.line([(0, 780), (W, 780)], OUT, 4)
    for xx in range(0, W, 240):
        c.line([(xx, 800), (xx - 40, 960)], (56, 58, 82), 3)
    c.rect(0, 960, W, 990, (50, 52, 74), None)
    c.line([(0, 960), (W, 960)], OUT, 5)
    c.rect(0, 990, W, H, (28, 30, 46), None)
    for xx in range(40, W, 260):
        c.rect(xx, 1030, xx + 140, 1044, (200, 180, 100), None)
    for x in (300, 1000, 1700):
        c.overlay(lambda l, x=x: l.poly([(x - 30, 440), (x + 30, 440), (x + 230, 960), (x - 230, 960)], (255, 226, 140, 255), None), 0.18)
        lamp_post(c, x, 800, True)


DRAWERS = {"room": draw_room, "classroom": draw_classroom, "street": draw_street, "park": draw_park, "cafe": draw_cafe,
           "rooftop": draw_rooftop, "skatepark": draw_skatepark, "living_room": draw_living_room, "market": draw_market,
           "night_street": draw_night_street}
_cache = {}


def background(name):
    """BGR numpy (1080x1920). Har location hamesha ek jaisa."""
    if name not in DRAWERS:
        name = "room"
    if name not in _cache:
        seed = sum(ord(ch) for ch in name) * 97
        c = Cv()
        DRAWERS[name](c, random.Random(seed))
        _cache[name] = c.result()
    return _cache[name]


# ------------------------------------------------------------------ props (chhote icons, 300x300 RGBA)
def _prop(fn):
    c = Cv(300, 300, None)
    fn(c)
    return c.result(rgba=True)


def p_pizza(c):
    c.poly([(150, 270), (30, 70), (270, 70)], (250, 200, 90), OUT, 6)
    c.rect(30, 56, 270, 86, (222, 150, 70), r=14, w=6)
    for x, y in [(130, 130), (180, 150), (150, 200), (110, 100), (190, 100)]:
        c.circ(x, y, 16, (210, 60, 60), OUT, 4)


def p_burger(c):
    c.rect(40, 70, 260, 140, (226, 160, 80), r=50, w=6)
    c.rect(36, 140, 264, 165, (110, 200, 90), r=12, w=6)
    c.rect(44, 165, 256, 205, (120, 70, 46), r=14, w=6)
    c.rect(36, 205, 264, 228, (250, 210, 80), r=10, w=6)
    c.rect(48, 228, 252, 270, (226, 160, 80), r=24, w=6)


def p_cake(c):
    c.rect(50, 150, 250, 260, (250, 214, 226), r=14, w=6)
    c.rect(70, 90, 230, 150, (250, 240, 226), r=14, w=6)
    c.rect(50, 150, 250, 176, (214, 90, 130), None)
    for x in (110, 150, 190):
        c.rect(x - 5, 52, x + 5, 90, (90, 180, 240), None)
        c.poly([(x, 24), (x - 8, 50), (x + 8, 50)], (255, 190, 60), OUT, 3)


def p_phone(c):
    c.rect(80, 20, 220, 280, (52, 56, 74), r=26, w=6)
    c.rect(92, 52, 208, 248, (110, 190, 250), r=10, w=3)
    c.circ(150, 266, 7, (200, 200, 210), None)
    c.rect(110, 80, 190, 108, (250, 250, 250), r=8, w=3)
    c.rect(110, 124, 170, 148, (250, 250, 250), r=8, w=3)


def p_laptop(c):
    c.rect(60, 70, 240, 190, (60, 66, 84), r=10, w=6)
    c.rect(72, 82, 228, 178, (30, 40, 48), r=4, w=2)
    for i in range(4):
        c.rect(84, 94 + i * 18, 84 + [90, 60, 110, 40][i], 102 + i * 18, (90, 230, 140), None)
    c.poly([(30, 270), (270, 270), (240, 190), (60, 190)], (196, 200, 214), OUT, 6)


def p_football(c):
    c.circ(150, 150, 110, (250, 250, 250), OUT, 6)
    c.poly([(150, 90), (200, 128), (182, 186), (118, 186), (100, 128)], (40, 44, 60), OUT, 4)
    for a in range(5):
        x, y = 150 + 108 * math.cos(math.radians(a * 72 - 90)), 150 + 108 * math.sin(math.radians(a * 72 - 90))
        c.line([(150 + 60 * math.cos(math.radians(a * 72 - 90)), 150 + 60 * math.sin(math.radians(a * 72 - 90))), (x, y)], OUT, 4)


def p_money(c):
    for dy, rot in [(-30, 0), (0, 0), (30, 0)]:
        c.rect(40, 100 + dy, 260, 190 + dy, (110, 190, 120), r=8, w=5)
        c.circ(150, 145 + dy, 28, (160, 220, 150), OUT, 4)
    c.text(150, 145 + 30, "$", 44, (40, 90, 50))


def p_trophy(c):
    c.poly([(80, 40), (220, 40), (205, 150), (150, 190), (95, 150)], (250, 204, 60), OUT, 6)
    c.line([(80, 60), (40, 60), (50, 120), (96, 130)], OUT, 6)
    c.line([(220, 60), (260, 60), (250, 120), (204, 130)], OUT, 6)
    c.rect(138, 190, 162, 235, (230, 170, 40), None)
    c.rect(90, 235, 210, 275, (90, 94, 120), r=8, w=6)


def p_gift(c):
    c.rect(50, 120, 250, 270, (230, 80, 100), r=8, w=6)
    c.rect(40, 90, 260, 135, (250, 110, 130), r=8, w=6)
    c.rect(134, 90, 166, 270, (250, 214, 90), None)
    c.ell(80, 30, 150, 92, None, OUT, 8)
    c.ell(150, 30, 220, 92, None, OUT, 8)


def p_books(c):
    for i, (col, w_) in enumerate([((220, 80, 80), 200), ((90, 150, 230), 220), ((250, 200, 80), 190)]):
        c.rect(150 - w_ / 2, 200 - i * 62, 150 + w_ / 2, 258 - i * 62, col, r=6, w=5)
        c.rect(150 - w_ / 2 + 14, 216 - i * 62, 150 + w_ / 2 - 14, 226 - i * 62, (250, 250, 240), None)


def p_balloon(c):
    c.ell(80, 20, 220, 200, (240, 80, 110), OUT, 6)
    c.poly([(150, 200), (136, 224), (164, 224)], (240, 80, 110), OUT, 4)
    c.line([(150, 224), (140, 260), (160, 280)], OUT, 4)
    c.ell(112, 50, 138, 100, (255, 170, 190), None)


def p_clock(c):
    c.circ(150, 150, 110, (250, 248, 240), OUT, 8)
    for a in range(12):
        x0, y0 = 150 + 92 * math.cos(math.radians(a * 30)), 150 + 92 * math.sin(math.radians(a * 30))
        x1, y1 = 150 + 104 * math.cos(math.radians(a * 30)), 150 + 104 * math.sin(math.radians(a * 30))
        c.line([(x0, y0), (x1, y1)], OUT, 4)
    c.line([(150, 150), (150, 80)], OUT, 8)
    c.line([(150, 150), (200, 170)], OUT, 8)
    c.circ(150, 150, 9, OUT, None)


def p_key(c):
    c.circ(90, 150, 60, (250, 204, 60), OUT, 6)
    c.circ(90, 150, 22, (255, 255, 255), OUT, 5)
    c.rect(140, 138, 280, 164, (250, 204, 60), r=6, w=6)
    c.rect(220, 164, 244, 200, (250, 204, 60), None)
    c.rect(256, 164, 280, 192, (250, 204, 60), None)


def p_camera(c):
    c.rect(30, 90, 270, 240, (70, 74, 96), r=24, w=6)
    c.rect(100, 60, 180, 96, (70, 74, 96), r=10, w=6)
    c.circ(150, 165, 56, (190, 210, 230), OUT, 6)
    c.circ(150, 165, 30, (60, 90, 150), OUT, 4)
    c.circ(236, 118, 10, (250, 90, 90), None)


def p_icecream(c):
    c.poly([(90, 130), (210, 130), (150, 280)], (230, 180, 100), OUT, 6)
    c.circ(150, 108, 66, (250, 170, 200), OUT, 6)
    c.circ(150, 50, 30, (250, 170, 200), OUT, 5)
    c.circ(168, 22, 12, (230, 50, 70), OUT, 3)


def p_skateboard(c):
    c.rect(20, 120, 280, 175, (234, 150, 60), r=27, w=6)
    c.text(150, 148, "SZ", 36, (90, 40, 20))
    for x in (70, 230):
        c.circ(x, 205, 18, (240, 240, 245), OUT, 5)


def p_backpack(c):
    c.rect(70, 50, 230, 270, (80, 130, 220), r=50, w=6)
    c.rect(100, 160, 200, 240, (60, 100, 190), r=16, w=5)
    c.rect(120, 20, 180, 62, None, OUT, 8, r=20)
    c.line([(100, 200), (200, 200)], OUT, 4)


def p_exam(c):
    c.rect(60, 20, 240, 280, (252, 250, 240), r=8, w=6)
    for i in range(5):
        c.line([(84, 170 + i * 20), (216, 170 + i * 20)], (150, 150, 170), 3)
    c.text(150, 100, "F", 120, (220, 50, 60))
    c.circ(150, 100, 64, None, (220, 50, 60), 8)


def p_umbrella(c):
    c.poly([(30, 150), (60, 70), (150, 30), (240, 70), (270, 150), (225, 130), (188, 150), (150, 130), (112, 150), (75, 130)], (230, 80, 100), OUT, 6)
    c.line([(150, 130), (150, 250), (126, 276)], OUT, 8)


PROPS = {"pizza": p_pizza, "burger": p_burger, "cake": p_cake, "phone": p_phone, "laptop": p_laptop, "football": p_football,
         "money": p_money, "trophy": p_trophy, "gift": p_gift, "books": p_books, "balloon": p_balloon, "clock": p_clock,
         "key": p_key, "camera": p_camera, "icecream": p_icecream, "skateboard": p_skateboard, "backpack": p_backpack,
         "exam": p_exam, "umbrella": p_umbrella}
_pcache = {}


def prop_sprite(name):
    if name not in PROPS:
        return None
    if name not in _pcache:
        _pcache[name] = _prop(PROPS[name])
    return _pcache[name]


# ------------------------------------------------------------------ fx (character ke upar aane wale symbol), 260x260
def f_exclaim(c):
    c.poly([(110, 20), (150, 20), (142, 150), (118, 150)], (240, 60, 60), OUT, 6)
    c.circ(130, 196, 20, (240, 60, 60), OUT, 6)


def f_question(c):
    c.text(130, 120, "?", 250, (70, 120, 240), OUT)


def f_sweat(c):
    for x, y, s in [(70, 70, 1.0), (170, 130, 0.8)]:
        c.poly([(x, y - 50 * s), (x - 28 * s, y + 10 * s), (x + 28 * s, y + 10 * s)], (120, 200, 250), OUT, 5)
        c.circ(x, y + 10 * s, 28 * s, (120, 200, 250), OUT, 5)


def f_anger(c):
    for dx, dy in [(-22, -22), (22, 22)]:
        c.line([(130 + dx - 40, 130 + dy - 40), (130 + dx + 40, 130 + dy + 40)], (230, 40, 50), 22)
        c.line([(130 + dx - 40, 130 + dy + 40), (130 + dx + 40, 130 + dy - 40)], (230, 40, 50), 22)


def f_hearts(c):
    for x, y, s in [(80, 160, 1.0), (170, 90, 0.8), (110, 50, 0.6)]:
        c.circ(x - 18 * s, y - 8 * s, 22 * s, (250, 90, 130), OUT, 5)
        c.circ(x + 18 * s, y - 8 * s, 22 * s, (250, 90, 130), OUT, 5)
        c.poly([(x - 38 * s, y), (x + 38 * s, y), (x, y + 42 * s)], (250, 90, 130), OUT, 5)
        c.circ(x - 18 * s, y - 8 * s, 18 * s, (250, 90, 130), None)
        c.circ(x + 18 * s, y - 8 * s, 18 * s, (250, 90, 130), None)


def _star(c, x, y, r, col):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.42
        a = math.radians(i * 36 - 90)
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    c.poly(pts, col, OUT, 4)


def f_sparkle(c):
    _star(c, 100, 150, 56, (255, 220, 70))
    _star(c, 180, 80, 36, (255, 240, 130))
    _star(c, 190, 190, 28, (255, 220, 70))


def f_dots(c):
    c.ell(20, 60, 240, 170, (255, 255, 255), OUT, 6)
    c.poly([(70, 160), (50, 215), (110, 166)], (255, 255, 255), OUT, 6)
    c.rect(66, 150, 112, 168, (255, 255, 255), None)
    for x in (80, 130, 180):
        c.circ(x, 115, 14, OUT, None)


def f_zzz(c):
    for x, y, s in [(60, 190, 70), (110, 120, 90), (170, 50, 110)]:
        c.text(x, y, "Z", s, (255, 255, 255), OUT)


def f_boom(c):
    pts = []
    for i in range(24):
        r = 124 if i % 2 == 0 else 70
        a = math.radians(i * 15)
        pts.append((130 + r * math.cos(a), 130 + r * math.sin(a)))
    c.poly(pts, (255, 214, 60), OUT, 7)
    pts = []
    for i in range(24):
        r = 84 if i % 2 == 0 else 46
        a = math.radians(i * 15 + 7)
        pts.append((130 + r * math.cos(a), 130 + r * math.sin(a)))
    c.poly(pts, (255, 120, 50), None)
    c.text(130, 134, "BOOM", 46, (255, 255, 255), OUT)


def f_idea(c):
    c.circ(130, 100, 64, (255, 230, 90), OUT, 6)
    c.rect(104, 160, 156, 206, (200, 204, 216), r=8, w=5)
    c.line([(106, 100), (130, 76), (154, 100)], OUT, 4)
    for a in (-60, -20, 20, 60):
        x0, y0 = 130 + 82 * math.sin(math.radians(a)), 100 - 82 * math.cos(math.radians(a))
        x1, y1 = 130 + 112 * math.sin(math.radians(a)), 100 - 112 * math.cos(math.radians(a))
        c.line([(x0, y0), (x1, y1)], (255, 200, 40), 6)


def f_laugh(c):
    c.text(130, 130, "HAHA", 80, (255, 220, 60), OUT)


def f_skull(c):
    c.circ(130, 110, 80, (245, 245, 240), OUT, 6)
    c.rect(96, 170, 164, 220, (245, 245, 240), r=8, w=6)
    c.circ(100, 110, 22, OUT, None)
    c.circ(160, 110, 22, OUT, None)
    c.poly([(130, 130), (118, 156), (142, 156)], OUT, None)


FX = {"exclaim": f_exclaim, "question": f_question, "sweat": f_sweat, "anger": f_anger, "hearts": f_hearts, "sparkle": f_sparkle,
      "dots": f_dots, "zzz": f_zzz, "boom": f_boom, "idea": f_idea, "laugh": f_laugh, "skull": f_skull}
_fcache = {}


def fx_sprite(name):
    if name not in FX:
        return None
    if name not in _fcache:
        c = Cv(260, 260, None)
        FX[name](c)
        _fcache[name] = c.result(rgba=True)
    return _fcache[name]
