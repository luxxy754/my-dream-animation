"""Puppet animation: character ki PNG images ko code se chalata, uchhalta, hilata hai. Background/props/effects world.py se.

Har character: breathing + bolte waqt awaaz ke saath uchhal (lip-sync), emotion ke hisaab se tint/hilna, action (jump, fall, spin...),
entry (slide/pop), symbol effects (!, ?, BOOM...), prop pop-in, camera zoom/pan/shake.
"""
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import world

BASE_H = 640           # 173 cm wale character ki screen par unchai (px, 1080p world mein)
FEET_Y = world.GROUND + 12
OUTS = {"long": (1920, 1080), "short": (1080, 1920)}
TINTS = {"angry": (0.80, 0.84, 1.0), "sad": (1.0, 0.95, 0.86), "scared": (1.0, 1.0, 0.92)}  # BGR multiply


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def pop_scale(t):
    if t <= 0:
        return 0.0
    if t < 0.16:
        return 1.25 * ease_out(t / 0.16)
    if t < 0.30:
        return 1.25 - 0.25 * ease_out((t - 0.16) / 0.14)
    return 1.0 + 0.025 * math.sin(t * 6)


def _premult(im):
    a = im[:, :, 3:4].astype(np.float32) / 255.0
    out = im.copy()
    out[:, :, :3] = (im[:, :, :3].astype(np.float32) * a).astype(np.uint8)
    return out


def load_sprite(path, target_h):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None:
        return None
    if im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    if im.shape[2] == 3 or (im.shape[2] == 4 and im[:, :, 3].min() > 250):  # transparency nahi -> background khud hatao
        from tools.cutout import cutout
        im = cutout(im[:, :, :3])
    ys, xs = np.where(im[:, :, 3] > 8)
    if len(ys):
        im = im[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    sc = target_h / im.shape[0]
    im = cv2.resize(im, (max(2, int(im.shape[1] * sc)), target_h), interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_CUBIC)
    return _premult(im)


class Char:
    def __init__(self, d):
        self.d = d
        self.name = d["name"]
        self.h = int(BASE_H * max(0.5, min(1.5, d["height_cm"] / 173.0)))
        self.paths = d["poses"]
        self.has_art = d["has_art"]
        self._c = {}
        self.color = d["color"]

    def sprite(self, emotion, talking):
        if not self.paths:
            return None
        base = emotion if emotion in self.paths else ("idle" if "idle" in self.paths else sorted(self.paths)[0])
        key = base
        if talking:
            for k in (base + "_talk", "talk"):
                if k in self.paths:
                    key = k
                    break
        if key not in self._c:
            self._c[key] = load_sprite(self.paths[key], self.h)
        return self._c[key]


def blend(frame, spr, x0, y0, tint=None, alpha=1.0, flash=0.0):
    """premultiplied BGRA spr ko frame par (x0,y0) se milao (clipping ke saath)."""
    h, w = spr.shape[:2]
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(frame.shape[1], x0 + w), min(frame.shape[0], y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    s = spr[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0].astype(np.float32)
    rgb, a = s[:, :, :3], s[:, :, 3:4] / 255.0
    if tint is not None:
        rgb = rgb * np.array(tint, np.float32)
    if flash:
        rgb = rgb + 255.0 * a * flash
    roi = frame[fy0:fy1, fx0:fx1].astype(np.float32)
    out = rgb * alpha + roi * (1 - a * alpha)
    frame[fy0:fy1, fx0:fx1] = np.clip(out, 0, 255).astype(np.uint8)


def transform(spr, cx, feet, rot, sx, sy, flip):
    """pairon (neeche beech) ko pivot maan kar spr ko ghumao/failao; (warped, x0, y0) wapas."""
    h, w = spr.shape[:2]
    fx = -sx if flip else sx
    th = math.radians(rot)
    c, s = math.cos(th), math.sin(th)
    # sprite coords -> frame: translate(-w/2,-h) -> scale -> rotate(clockwise rot) -> translate(cx,feet)
    A = np.array([[c, -s], [s, c]]) @ np.array([[fx, 0], [0, sy]])
    corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float32) - [w / 2, h]
    pts = corners @ A.T + [cx, feet]
    x0, y0 = int(math.floor(pts[:, 0].min())) - 2, int(math.floor(pts[:, 1].min())) - 2
    x1, y1 = int(math.ceil(pts[:, 0].max())) + 2, int(math.ceil(pts[:, 1].max())) + 2
    off = np.array([cx - x0, feet - y0])
    M = np.zeros((2, 3), np.float32)
    M[:, :2] = A
    M[:, 2] = off - A @ np.array([w / 2, h])
    out = cv2.warpAffine(spr, M, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    return out, x0, y0


# ------------------------------------------------------------------ motion
def motion(action, emo, tl, tg, mouth, speaking, ph):
    """return dx, dy(px, minus = upar), rot(deg, + = ghadi ki simt), sx, sy, flash"""
    dx = dy = rot = flash = 0.0
    sx = sy = 1.0
    br = math.sin(tg * 2.2 + ph)
    sy += 0.012 * br
    sx -= 0.006 * br
    if speaking:
        sy += 0.045 * mouth
        sx -= 0.022 * mouth
        dy -= 7 * mouth
        rot += 1.4 * math.sin(tg * 5 + ph) * mouth
    ab = abs(math.sin(tg * 4 + ph))
    if emo == "happy":
        dy -= 8 * ab
    elif emo == "excited":
        dy -= 24 * abs(math.sin(tg * 7 + ph))
        rot += 2 * math.sin(tg * 7 + ph)
    elif emo == "sad":
        sy *= 0.96
        dy += 8
        rot -= 3
    elif emo == "angry":
        dx += 5 * math.sin(tg * 38 + ph)
        sy += 0.02 * abs(math.sin(tg * 9))
    elif emo == "scared":
        dx += 4 * math.sin(tg * 50 + ph)
        sy *= 0.97
        rot -= 3
    elif emo == "shocked":
        k = max(0.0, 1 - tl / 0.45)
        sx += 0.16 * k
        sy += 0.16 * k
        dy -= 60 * max(0.0, 1 - tl / 0.28) ** 1.5
        flash = 0.5 * max(0.0, 1 - tl / 0.12)
    elif emo == "confused":
        rot += 4 * math.sin(tg * 1.6 + ph)
    elif emo == "smug":
        rot -= 2.5
        sy *= 1.015
    elif emo == "laugh":
        dy -= 16 * abs(math.sin(tg * 9 + ph))
        rot -= 5 + 4 * math.sin(tg * 9 + ph)
    # action
    if action == "jump":
        u = (tl % 0.95) / 0.95
        dy -= 270 * 4 * u * (1 - u)
        if u > 0.9 or u < 0.06:
            sy *= 0.9
            sx *= 1.08
    elif action == "hop":
        dy -= 60 * abs(math.sin(tg * 6 + ph))
    elif action in ("walk", "run"):
        f = 8 if action == "walk" else 13
        dy -= (16 if action == "walk" else 30) * abs(math.sin(tg * f))
        rot += (3 if action == "walk" else -8) * math.sin(tg * f)
    elif action == "shake":
        dx += 14 * math.sin(tg * 40)
    elif action == "spin":
        sx *= math.cos(2 * math.pi * min(tl / 0.8, 1.0))
    elif action == "fall":
        u = ease_out(tl / 0.35)
        rot -= 88 * u
        dx -= 70 * u
        dy += 20 * u
        if 0.35 < tl < 0.7:
            dy -= 40 * math.sin(math.pi * (tl - 0.35) / 0.35)
    elif action == "dance":
        rot += 9 * math.sin(tg * 6)
        dy -= 22 * abs(math.sin(tg * 6))
        sx += 0.05 * math.sin(tg * 12)
    elif action == "point":
        rot += 6
        dx += 20
        dy -= 8 * abs(math.sin(tg * 5))
    elif action == "nod":
        dy += 10 * math.sin(tg * 5)
        sy += 0.02 * math.sin(tg * 5)
    elif action == "dizzy":
        rot += 10 * math.sin(tg * 3)
        dx += 22 * math.sin(tg * 3 + 1)
    elif action == "float":
        dy -= 50 + 12 * math.sin(tg * 2)
    elif action == "tremble":
        dx += 4 * math.sin(tg * 60)
    elif action == "slump":
        sy *= 0.9
        dy += 30
        rot += 6
    return dx, dy, rot, sx, sy, flash


def layout(n, kind):
    xs = {1: [960], 2: [640, 1280], 3: [420, 960, 1500], 4: [320, 740, 1180, 1600], 5: [260, 610, 960, 1310, 1660]}[min(max(n, 1), 5)]
    if kind == "short":
        xs = [960 + (x - 960) * 0.5 for x in xs]
    return xs


def _text_sprite(text, size, fill=(255, 255, 255), stroke=(0, 0, 0)):
    f = ImageFont.truetype(world.FONT_BOLD, size) if world.FONT_BOLD else ImageFont.load_default()
    d0 = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    l, t, r, b = d0.textbbox((0, 0), text, font=f, stroke_width=4)
    im = Image.new("RGBA", (r - l + 16, b - t + 16), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((8 - l, 8 - t), text, font=f, fill=fill + (255,), stroke_width=4, stroke_fill=stroke + (255,))
    a = np.array(im)
    return _premult(a[..., [2, 1, 0, 3]].copy())


def scaled(spr, k):
    k = max(0.02, k)
    return cv2.resize(spr, (max(2, int(spr.shape[1] * k)), max(2, int(spr.shape[0] * k))),
                      interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_LINEAR)


class Stage:
    def __init__(self, kind, chars):
        self.kind = kind
        self.OW, self.OH = OUTS[kind]
        self.chars = {c.name: c for c in chars}
        self.cam_x = 960.0
        self._fx, self._props, self._tags = {}, {}, {}

    # sprites jo premultiplied chahiye
    def fx(self, name):
        if name not in self._fx:
            s = world.fx_sprite(name)
            self._fx[name] = None if s is None else _premult(s)
        return self._fx[name]

    def prop(self, name):
        if name not in self._props:
            s = world.prop_sprite(name)
            self._props[name] = None if s is None else _premult(s)
        return self._props[name]

    def tag(self, text):
        if text not in self._tags:
            self._tags[text] = _text_sprite(text, 34)
        return self._tags[text]

    def begin_scene(self, sc):
        self.bg = world.background(sc["loc"])
        xs = layout(len(sc["on"]), self.kind)
        self.pos = {n: x for n, x in zip(sc["on"], xs)}

    def draw_char(self, f, name, x, ts, tl, tg, emo, action, speaking, mouth, enter_mode, scale_mul, ph):
        ch = self.chars[name]
        spr = ch.sprite(emo, speaking and mouth > 0.4)
        if spr is None:
            return None
        dx, dy, rot, sx, sy, flash = motion(action, emo, tl, tg, mouth, speaking, ph)
        # entry
        if enter_mode == "slide" and ts < 0.55:
            k = 1 - ease_out(ts / 0.5)
            edge = -400 if x < 960 else 2320
            dx += (edge - x) * k
            dy -= 50 * math.sin(math.pi * min(ts / 0.5, 1.0))
        elif enter_mode == "pop":
            k = pop_scale(ts - 0.05)
            sx *= k
            sy *= k
            if k <= 0:
                return None
        flip = x > 960 and ch.d.get("flip_ok", True)
        # shadow
        lift = max(0.0, -dy)
        sh = max(0.35, 1 - lift / 500.0)
        sw, sh_h = int(spr.shape[1] * 0.42 * sh), int(16 * sh)
        x0, y0 = int(x + dx - sw), int(FEET_Y - sh_h)
        if 0 <= y0 < f.shape[0] - 2 * sh_h and x0 > 0 and x0 + 2 * sw < f.shape[1]:
            sub = f[y0:y0 + 2 * sh_h, x0:x0 + 2 * sw]
            ov = sub.copy()
            cv2.ellipse(ov, (sw, sh_h), (sw, sh_h), 0, 0, 360, (20, 20, 30), -1, cv2.LINE_AA)
            cv2.addWeighted(ov, 0.28, sub, 0.72, 0, sub)
        tint = TINTS.get(emo) if (emo not in ch.paths) else None
        warped, wx, wy = transform(spr, x + dx, FEET_Y + dy, rot, sx * scale_mul, sy * scale_mul, flip)
        blend(f, warped, wx, wy, tint=tint, flash=flash)
        return x + dx, FEET_Y + dy - spr.shape[0] * sy * scale_mul  # sar ke upar ka point

    def draw_icon(self, f, spr, cx, cy, k, wobble=0.0):
        if spr is None or k <= 0:
            return
        s = scaled(spr, k)
        h, w = s.shape[:2]
        if wobble:
            s, wx, wy = transform(s, w / 2, h, wobble, 1, 1, False)
            blend(f, s, int(cx - w / 2 + wx), int(cy - h / 2 + wy))
        else:
            blend(f, s, int(cx - w / 2), int(cy - h / 2))

    def frame(self, sc, ln, ts, tl, tg, mouth, speaking, sprog, punch=0.0):
        """sc: scene entry, ln: line entry, ts: scene mein second, tl: line mein second. Output frame (camera ke baad)."""
        f = self.bg.copy()
        spk = ln["speaker"]
        order = [n for n in sc["on"] if n != spk] + ([spk] if spk in sc["on"] else [])
        heads = {}
        for n in order:
            if n not in self.chars:
                continue
            emo, act = ln["states"].get(n, ("neutral", "idle"))
            is_spk = n == spk
            ph = (sum(map(ord, n)) % 17) * 0.7
            enter = sc["enter"].get(n)
            h = self.draw_char(f, n, self.pos[n], ts, tl if is_spk else max(tl, 0.0), tg, emo, act, is_spk and speaking,
                               mouth if is_spk else 0.0, enter, 1.04 if is_spk else 0.97, ph)
            if h:
                heads[n] = h
        # prop
        if ln.get("prop") and ln["prop"] != "none":
            spr = self.prop(ln["prop"])
            px = 1500 if self.pos.get(spk, 960) <= 960 else 420
            if self.kind == "short":
                px = self.pos.get(spk, 960) + (170 if self.pos.get(spk, 960) <= 960 else -170)
            self.draw_icon(f, spr, px, 400, pop_scale(tl - 0.1) * (0.95 if self.kind == "long" else 0.6), 4 * math.sin(tg * 3))
        # fx
        fx = ln.get("fx")
        if fx and fx != "none" and 0.1 < tl < 2.0 and spk in heads:
            hx, hy = heads[spk]
            big = 1.5 if fx == "boom" else 0.95
            ky = pop_scale(tl - 0.1) * big
            if fx == "boom":
                self.draw_icon(f, self.fx(fx), hx, hy + 330, ky if tl < 1.1 else 0)
            else:
                off = {"sweat": (120, 40), "anger": (110, 20), "hearts": (0, -30), "zzz": (110, 10)}.get(fx, (0, 0))
                self.draw_icon(f, self.fx(fx), hx + off[0], hy - 40 + off[1] - 12 * math.sin(tl * 4), ky)
        # off-screen awaaz
        if speaking and (spk not in self.chars or not self.chars[spk].has_art):
            cx = self.cam_x + (700 if self.kind == "long" else 130)
            self.draw_icon(f, self.fx("dots"), cx, 250, pop_scale(tl) * 0.9)
            self.draw_icon(f, self.tag(spk.upper()), cx, 360, 1.0)
        # white flash on scene cut
        if sc.get("cut") and ts < 0.28:
            f = cv2.addWeighted(f, 1 - 0.75 * (1 - ts / 0.28), np.full_like(f, 255), 0.75 * (1 - ts / 0.28), 0)
        return self.camera(f, self.pos.get(spk, 960), sprog, punch, ln.get("sfx") in ("crash", "thud", "bonk") and tl < 0.35, tl, tg)

    def camera(self, f, spk_x, sprog, punch, shake, tl, tg):
        z = 1.0 + 0.035 * sprog + punch
        if self.kind == "long":
            target = 960 + (spk_x - 960) * 0.15
            self.cam_x += (target - self.cam_x) * 0.08
            ww, hh = 1920 / z, 1080 / z
        else:
            target = spk_x
            self.cam_x += (target - self.cam_x) * 0.12
            ww, hh = 607.5 / z, 1080 / z
        cx = min(max(self.cam_x, ww / 2), 1920 - ww / 2)
        cy = 540 + (0 if self.kind == "long" else 60)
        cy = min(max(cy, hh / 2), 1080 - hh / 2)
        if shake:
            cx += 14 * math.sin(tl * 70) * (1 - tl / 0.35)
            cy += 10 * math.cos(tl * 63) * (1 - tl / 0.35)
        x0, y0 = cx - ww / 2, cy - hh / 2
        sx, sy = self.OW / ww, self.OH / hh
        M = np.float32([[sx, 0, -x0 * sx], [0, sy, -y0 * sy]])
        return cv2.warpAffine(f, M, (self.OW, self.OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
