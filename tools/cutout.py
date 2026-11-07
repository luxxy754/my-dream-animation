"""Character image ka background hata kar transparent PNG banata hai (koi API / AI model nahi, sirf OpenCV).

Use:  python tools/cutout.py input.jpg characters/shazy/idle.png [--crop x0,y0,x1,y1] [--tol 26]

- Agar image mein ek hi character hai aur peechhe saaf/ek rang ka background hai -> sirf input/output do.
- Character sheet (bohat saare poses) ho to --crop se ek pose ka dabba chunein (pixels mein).
- Aakhir mein sirf sab se bada hissa rakha jata hai (aas paas ki sketches/decoration khud hat jati hain).
"""
import argparse

import cv2
import numpy as np


def cutout(img, tol=26, pad=6):
    h, w = img.shape[:2]
    work = cv2.copyMakeBorder(img, 1, 1, 1, 1, cv2.BORDER_REPLICATE)
    bg = np.zeros((h + 4, w + 4), np.uint8)
    seeds = [(0, 0), (w, 0), (0, h), (w, h)] + [(x, 0) for x in range(0, w, max(1, w // 12))] + \
            [(x, h) for x in range(0, w, max(1, w // 12))] + [(0, y) for y in range(0, h, max(1, h // 12))] + \
            [(w, y) for y in range(0, h, max(1, h // 12))]
    for sx, sy in seeds:
        if bg[sy + 1, sx + 1]:
            continue
        m = np.zeros((h + 4, w + 4), np.uint8)
        cv2.floodFill(work.copy(), m, (sx, sy), (0, 0, 0), (tol,) * 3, (tol,) * 3,
                      cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8))
        bg |= m
    fg = (bg[1:h + 1, 1:w + 1] == 0).astype(np.uint8) * 255
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    if n > 1:
        k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        fg = (lab == k).astype(np.uint8) * 255
    # andar ke chhote surakh bharo (aankhon/kapdon ke safed hisse na kategi)
    inv = 255 - fg
    n, lab, stats, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    for k in range(1, n):
        x, y, ww, hh, a = stats[k]
        if x > 0 and y > 0 and x + ww < w and y + hh < h:
            fg[lab == k] = 255
    fg = cv2.GaussianBlur(fg, (0, 0), 1.1)
    rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    rgba[:, :, 3] = fg
    ys, xs = np.where(fg > 8)
    y0, y1, x0, x1 = max(0, ys.min() - pad), min(h, ys.max() + pad), max(0, xs.min() - pad), min(w, xs.max() + pad)
    return rgba[y0:y1, x0:x1]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--crop", default="")
    ap.add_argument("--tol", type=int, default=26)
    a = ap.parse_args()
    im = cv2.imread(a.src, cv2.IMREAD_COLOR)
    if a.crop:
        x0, y0, x1, y1 = [int(v) for v in a.crop.split(",")]
        im = im[y0:y1, x0:x1]
    out = cutout(im, a.tol)
    cv2.imwrite(a.dst, out)
    print("saved", a.dst, out.shape[1], "x", out.shape[0])
