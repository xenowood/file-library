#!/usr/bin/env python3
"""Render the PNG app icons (48/64/128/256) that match data/icons/hicolor/scalable/apps/file-library.svg.

Needs Pillow (python3-pil). Run from the project root:  python3 tools/render_icons.py
"""
import os
from PIL import Image, ImageDraw

K = 8
S = 128 * K
W = (255, 255, 255, 255)


def layer():
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def rr(d, x0, y0, x1, y1, r, fill):
    d.rounded_rectangle([x0 * K, y0 * K, x1 * K, y1 * K], radius=r * K, fill=fill)


def poly(d, pts, fill):
    d.polygon([(x * K, y * K) for x, y in pts], fill=fill)


base, d = layer()
rr(d, 0, 0, 128, 128, 28, (0xEE, 0xF2, 0xF7, 255))

left, d = layer()
rr(d, 14, 32, 66, 102, 6, (0x2F, 0x6F, 0xDD, 255))
poly(d, [(21, 64), (21, 84), (35, 74)], W)
left = left.rotate(14, center=(40 * K, 70 * K), resample=Image.BICUBIC)

right, d = layer()
rr(d, 62, 32, 114, 102, 6, (0xF0, 0x8A, 0x24, 255))
for y0, x1 in ((48, 106), (60, 106), (72, 98)):
    rr(d, 92, y0, x1, y0 + 5, 2, W)
right = right.rotate(-14, center=(88 * K, 70 * K), resample=Image.BICUBIC)

mid, d = layer()
rr(d, 38, 22, 90, 92, 6, (0x2F, 0xA3, 0x6B, 255))
d.ellipse([(76 - 5) * K, (40 - 5) * K, (76 + 5) * K, (40 + 5) * K], fill=W)
poly(d, [(45, 80), (59, 60), (69, 73), (75, 65), (85, 80)], W)

img = base
for x in (left, right, mid):
    img = Image.alpha_composite(img, x)

for size in (48, 64, 128, 256):
    out = os.path.join("data", "icons", "hicolor", f"{size}x{size}", "apps")
    os.makedirs(out, exist_ok=True)
    img.resize((size, size), Image.LANCZOS).save(os.path.join(out, "file-library.png"))
print("icons written")
