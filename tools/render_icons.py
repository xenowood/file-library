#!/usr/bin/env python3
"""Generate the File Library app icon: the scalable SVG and the PNG sizes.

Four fanned cards (video, music, image, document) on a light grey tile.
Both outputs are drawn from the same card list below, so they always match.

Needs Pillow (python3-pil). Run from the project root:  python3 tools/render_icons.py
"""
import os

from PIL import Image, ImageDraw

BG = "#d9dce1"
COLORS = {"v": "#2f6fdd", "i": "#2fa36b", "d": "#f08a24", "m": "#8e44ad"}

# White symbols, centred on (0, 0) and about 16 units tall.
GLYPHS = {
    "v": [("poly", [(-5, -8), (-5, 8), (8, 0)])],
    "i": [("poly", [(-9, 8), (-3, -2), (1, 4), (4, 0), (9, 8)]), ("ell", 4, -6, 2.7, 2.7)],
    "d": [("rect", -8, -8, 16, 3.4, 1.7), ("rect", -8, -1.7, 16, 3.4, 1.7), ("rect", -8, 4.6, 9, 3.4, 1.7)],
    "m": [("ell", -5, 6, 4.4, 3.3), ("ell", 4.2, 3.8, 4.4, 3.3),
          ("rect", -2.4, -8, 2.5, 14, 0), ("rect", 6.6, -10, 2.5, 14, 0),
          ("poly", [(-2.4, -8), (9.1, -10.6), (9.1, -6.2), (-2.4, -3.6)])],
}

PIVOT = (64, 122)
CARD_W, CARD_H = 42, 64
CARD_X, CARD_Y = 64 - CARD_W / 2, PIVOT[1] - 28 - CARD_H
# (kind, rotation in degrees, symbol x offset). Outer cards first, inner cards on top.
CARDS = [("v", -26, -8), ("d", 26, 8), ("m", -8.5, -8), ("i", 8.5, 0)]

# The whole icon is drawn 10% smaller than the canvas, centred, so it matches other app icons.
ICON_SCALE = 0.90
OFFSET = 64 * (1 - ICON_SCALE)

OUT = os.path.join("data", "icons", "hicolor")
SIZES = (48, 64, 128, 256)


def n(value):
    return f"{value:g}"


def glyph_svg(kind):
    parts = []
    for item in GLYPHS[kind]:
        if item[0] == "poly":
            pts = " L".join(f"{n(x)} {n(y)}" for x, y in item[1])
            parts.append(f'<path d="M{pts}Z" fill="#ffffff"/>')
        elif item[0] == "ell":
            parts.append(f'<ellipse cx="{n(item[1])}" cy="{n(item[2])}" rx="{n(item[3])}" '
                         f'ry="{n(item[4])}" fill="#ffffff"/>')
        else:
            rx = f' rx="{n(item[5])}"' if item[5] else ""
            parts.append(f'<rect x="{n(item[1])}" y="{n(item[2])}" width="{n(item[3])}" '
                         f'height="{n(item[4])}"{rx} fill="#ffffff"/>')
    return "\n      ".join(parts)


def build_svg():
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">',
             f'  <g transform="translate({n(OFFSET)} {n(OFFSET)}) scale({n(ICON_SCALE)})">',
             f'  <rect width="128" height="128" rx="28" fill="{BG}"/>']
    for kind, angle, dx in CARDS:
        lines.append(f'  <g transform="rotate({n(angle)} {PIVOT[0]} {PIVOT[1]})">')
        lines.append(f'    <rect x="{n(CARD_X)}" y="{n(CARD_Y)}" width="{CARD_W}" height="{CARD_H}" '
                     f'rx="6" fill="{COLORS[kind]}"/>')
        lines.append(f'    <g transform="translate({n(64 + dx)} {n(CARD_Y + 22)})">')
        lines.append(f"      {glyph_svg(kind)}")
        lines.append("    </g>")
        lines.append("  </g>")
    lines.append("  </g>")
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def build_png(scale=6):
    s = 128 * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, s, s], radius=28 * scale, fill=BG)
    for kind, angle, dx in CARDS:
        layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle([CARD_X * scale, CARD_Y * scale, (CARD_X + CARD_W) * scale,
                             (CARD_Y + CARD_H) * scale], radius=6 * scale, fill=COLORS[kind])
        gx, gy = 64 + dx, CARD_Y + 22

        def pt(x, y):
            return ((gx + x) * scale, (gy + y) * scale)

        for item in GLYPHS[kind]:
            if item[0] == "poly":
                d.polygon([pt(x, y) for x, y in item[1]], fill="#ffffff")
            elif item[0] == "ell":
                x0, y0 = pt(item[1] - item[3], item[2] - item[4])
                x1, y1 = pt(item[1] + item[3], item[2] + item[4])
                d.ellipse([x0, y0, x1, y1], fill="#ffffff")
            else:
                x0, y0 = pt(item[1], item[2])
                x1, y1 = pt(item[1] + item[3], item[2] + item[4])
                if item[5]:
                    d.rounded_rectangle([x0, y0, x1, y1], radius=item[5] * scale, fill="#ffffff")
                else:
                    d.rectangle([x0, y0, x1, y1], fill="#ffffff")
        # SVG rotates clockwise for positive angles, Pillow counter-clockwise
        layer = layer.rotate(-angle, center=(PIVOT[0] * scale, PIVOT[1] * scale), resample=Image.BICUBIC)
        img = Image.alpha_composite(img, layer)
    return img


def main():
    svg_dir = os.path.join(OUT, "scalable", "apps")
    os.makedirs(svg_dir, exist_ok=True)
    with open(os.path.join(svg_dir, "file-library.svg"), "w", encoding="utf-8") as fh:
        fh.write(build_svg())
    big = build_png()
    inner = int(big.width * ICON_SCALE)
    canvas = Image.new("RGBA", big.size, (0, 0, 0, 0))
    canvas.paste(big.resize((inner, inner), Image.LANCZOS), ((big.width - inner) // 2,) * 2)
    big = canvas
    for size in SIZES:
        folder = os.path.join(OUT, f"{size}x{size}", "apps")
        os.makedirs(folder, exist_ok=True)
        big.resize((size, size), Image.LANCZOS).save(os.path.join(folder, "file-library.png"))
    print("icons written")


if __name__ == "__main__":
    main()
