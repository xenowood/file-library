#!/usr/bin/env python3
"""Render docs/screenshot.png: an illustration of the File Library main window.

It shows four folders, one per file type (videos, images, documents, music),
and a list with files of those types. This is drawn with Pillow from sample
data, it is not a capture of the real application. Replace docs/screenshot.png
with a real screenshot when you like.

Needs Pillow (python3-pil) and the DejaVu Sans fonts. Run from the project root:
    python3 tools/render_screenshot.py
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 4                      # drawing scale, downsampled to 2x at the end
WIN_W, WIN_H = 1000, 700   # logical window size
MARGIN = 32
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# colors
BG = "#fafafa"
BAR = "#ebebeb"
TOOL = "#f3f3f3"
LINE = "#d3d3d3"
TEXT = "#2e2e2e"
DIM = "#777777"
ACCENT = "#3584e4"
CHIP_ON_BG, CHIP_ON_FG, CHIP_ON_BORDER = "#26a269", "#ffffff", "#1e8a58"
FOLDER_Y = "#e5a50a"
VIDEO_C, IMAGE_C, DOC_C, MUSIC_C = "#2f6fdd", "#2fa36b", "#f08a24", "#8e44ad"

_fonts = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_B if bold else FONT, int(size * S))
    return _fonts[key]


class Canvas:
    def __init__(self):
        self.w = (WIN_W + 2 * MARGIN) * S
        self.h = (WIN_H + 2 * MARGIN) * S
        self.img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    # logical coordinates are relative to the window's top-left corner
    def p(self, v):
        return int((v + MARGIN) * S)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, r=0, width=1):
        box = [self.p(x0), self.p(y0), self.p(x1), self.p(y1)]
        if r:
            self.d.rounded_rectangle(box, radius=int(r * S), fill=fill, outline=outline, width=int(width * S))
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=int(width * S))

    def line(self, x0, y0, x1, y1, fill=LINE, width=1):
        self.d.line([self.p(x0), self.p(y0), self.p(x1), self.p(y1)], fill=fill, width=int(width * S))

    def text(self, x, y, s, size=13, fill=TEXT, bold=False, anchor="lm"):
        self.d.text((self.p(x), self.p(y)), s, font=font(size, bold), fill=fill, anchor=anchor)

    def width(self, s, size=13, bold=False):
        return self.d.textlength(s, font=font(size, bold)) / S

    def poly(self, pts, fill):
        self.d.polygon([(self.p(x), self.p(y)) for x, y in pts], fill=fill)

    def ellipse(self, x0, y0, x1, y1, fill=None, outline=None, width=1):
        self.d.ellipse([self.p(x0), self.p(y0), self.p(x1), self.p(y1)],
                       fill=fill, outline=outline, width=int(width * S))

    def arc(self, x0, y0, x1, y1, start, end, fill, width=1.5):
        self.d.arc([self.p(x0), self.p(y0), self.p(x1), self.p(y1)], start, end,
                   fill=fill, width=int(width * S))


# ------------------------------------------------------------------ icons
def icon_folder(c, x, y, color=FOLDER_Y):
    c.rect(x, y + 2, x + 6, y + 6, fill=color, r=1)
    c.rect(x, y + 4, x + 16, y + 14, fill=color, r=2)


def icon_video(c, x, y):
    c.rect(x, y, x + 16, y + 14, fill=VIDEO_C, r=3)
    c.poly([(x + 6, y + 3.5), (x + 6, y + 10.5), (x + 11.5, y + 7)], "#ffffff")


def icon_image(c, x, y):
    c.rect(x, y, x + 16, y + 14, fill=IMAGE_C, r=3)
    c.poly([(x + 2, y + 12), (x + 6.5, y + 6), (x + 9.5, y + 10), (x + 11.5, y + 8), (x + 14, y + 12)], "#ffffff")
    c.ellipse(x + 10, y + 2.5, x + 13, y + 5.5, fill="#ffffff")


def icon_doc(c, x, y):
    c.rect(x + 1, y, x + 14, y + 15, fill=DOC_C, r=2)
    for i in range(3):
        c.rect(x + 4, y + 4 + i * 3.4, x + 11 - (i == 2) * 3, y + 5.6 + i * 3.4, fill="#ffffff")


def icon_music(c, x, y):
    c.rect(x, y, x + 16, y + 14, fill=MUSIC_C, r=3)
    c.ellipse(x + 3.5, y + 8, x + 8.2, y + 11.8, fill="#ffffff")
    c.rect(x + 7, y + 2.8, x + 8.3, y + 9.8, fill="#ffffff")
    c.poly([(x + 8.3, y + 2.8), (x + 12.4, y + 4.8), (x + 12.4, y + 6.8), (x + 8.3, y + 4.8)], "#ffffff")


KIND_ICON = {"v": icon_video, "i": icon_image, "d": icon_doc, "m": icon_music}


def icon_refresh(c, x, y, color=DIM, size=14):
    c.arc(x + 2, y + 2, x + size - 2, y + size - 2, 40, 330, color, 1.6)
    cx, cy = x + size - 2.2, y + size / 2 - 3.2
    c.poly([(cx - 3.2, cy - 0.5), (cx + 3.2, cy - 0.5), (cx, cy + 3.6)], color)


def icon_trash(c, x, y, color=DIM):
    c.rect(x + 2, y + 3, x + 12, y + 4.4, fill=color)
    c.rect(x + 5, y + 1, x + 9, y + 3, fill=color)
    c.rect(x + 3, y + 5, x + 11, y + 14, outline=color, r=1.5, width=1.4)
    c.line(x + 6, y + 7, x + 6, y + 12, fill=color, width=1.2)
    c.line(x + 8, y + 7, x + 8, y + 12, fill=color, width=1.2)


def icon_add_folder(c, x, y):
    icon_folder(c, x, y + 1, "#8a8a8a")
    c.rect(x + 9, y + 7, x + 17, y + 9, fill="#ffffff")
    c.rect(x + 12, y + 4, x + 14, y + 12, fill="#ffffff")


def icon_save(c, x, y):
    c.rect(x + 1, y + 1, x + 14, y + 14, fill="#8a8a8a", r=2)
    c.rect(x + 4, y + 1, x + 11, y + 5, fill="#ffffff")
    c.rect(x + 4, y + 8, x + 11, y + 14, fill="#ffffff")


def icon_export(c, x, y):
    c.line(x + 7.5, y + 9, x + 7.5, y + 1.5, fill="#8a8a8a", width=1.6)
    c.poly([(x + 3.5, y + 4.5), (x + 11.5, y + 4.5), (x + 7.5, y - 0.5)], "#8a8a8a")
    c.rect(x + 1.5, y + 8.5, x + 13.5, y + 14, outline="#8a8a8a", r=2, width=1.4)


def icon_info(c, x, y):
    c.ellipse(x, y, x + 14, y + 14, outline="#8a8a8a", width=1.4)
    c.rect(x + 6.2, y + 6, x + 7.8, y + 11, fill="#8a8a8a")
    c.ellipse(x + 6, y + 3, x + 8, y + 5, fill="#8a8a8a")


def icon_search(c, x, y):
    c.ellipse(x, y, x + 10, y + 10, outline=DIM, width=1.5)
    c.line(x + 9, y + 9, x + 14, y + 14, fill=DIM, width=1.8)


def icon_eye(c, x, y, color=DIM):
    """Flat show/hide icon, same style as the refresh and trash icons (14 px)."""
    cx, cy = x + 7, y + 7
    c.ellipse(cx - 7, cy - 4.6, cx + 7, cy + 4.6, outline=color, width=1.4)
    c.ellipse(cx - 2.2, cy - 2.2, cx + 2.2, cy + 2.2, fill=color)


def checkbox(c, x, y, checked):
    if checked:
        c.rect(x, y, x + 16, y + 16, fill=ACCENT, r=3)
        c.line(x + 4, y + 8.5, x + 7, y + 11.5, fill="#ffffff", width=1.8)
        c.line(x + 7, y + 11.5, x + 12.5, y + 4.8, fill="#ffffff", width=1.8)
    else:
        c.rect(x, y, x + 16, y + 16, fill="#ffffff", outline="#9a9a9a", r=3)


# ------------------------------------------------------------------ pieces
def button(c, x, y, w, label, icon):
    c.rect(x, y, x + w, y + 30, fill="#ffffff", outline="#c6c6c6", r=6)
    icon(c, x + 10, y + 8)
    c.text(x + 32, y + 15, label, 13)


def chip(c, x, y, label, on):
    w = c.width(label, 11) + 20
    if on:
        c.rect(x, y, x + w, y + 22, fill=CHIP_ON_BG, outline=CHIP_ON_BORDER, r=11)
        c.text(x + 10, y + 11, label, 11, CHIP_ON_FG)
    else:
        c.rect(x, y, x + w, y + 22, fill="#ffffff", outline="#c6c6c6", r=11)
        c.text(x + 10, y + 11, label, 11, "#555555")
    return x + w + 5


# ------------------------------------------------------------------ data
TYPE_LABELS = [("v", "Videos"), ("i", "Images"), ("d", "Documents"), ("m", "Music")]
FOLDERS = [
    ("Videos", "/home/user/Videos", "v"),
    ("Pictures", "/home/user/Pictures", "i"),
    ("Documents", "/home/user/Documents", "d"),
    ("Music", "/home/user/Music", "m"),
]
# (depth, kind, name, size_mb); "dir" rows have no size
TREE = [
    (0, "dir", "Videos", None),
    (1, "v", "holiday intro.mp4", 48.20),
    (1, "v", "interview.mkv", 812.55),
    (1, "dir", "Family", None),
    (2, "v", "birthday 2024.mov", 356.71),
    (0, "dir", "Pictures", None),
    (1, "i", "cover.jpg", 2.40),
    (1, "dir", "Trip", None),
    (2, "i", "beach.png", 6.80),
    (0, "dir", "Documents", None),
    (1, "d", "budget.pdf", 0.80),
    (1, "dir", "Contracts", None),
    (2, "d", "lease.odt", 0.40),
    (0, "dir", "Music", None),
    (1, "m", "Blue in Green.flac", 31.42),
    (1, "dir", "Live", None),
    (2, "m", "Encore.wav", 54.30),
]


def render():
    c = Canvas()
    status_y = WIN_H - 36

    # shadow
    shadow = Image.new("RGBA", c.img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [c.p(0), c.p(8), c.p(WIN_W), c.p(WIN_H + 8)], radius=12 * S, fill=(0, 0, 0, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14 * S))
    c.img = Image.alpha_composite(c.img, shadow)
    c.d = ImageDraw.Draw(c.img)

    # window + header bar
    c.rect(0, 0, WIN_W, WIN_H, fill=BG, outline="#c4c4c4", r=12)
    c.d.rounded_rectangle([c.p(0), c.p(0), c.p(WIN_W), c.p(46)], radius=12 * S, fill=BAR)
    c.rect(0, 30, WIN_W, 46, fill=BAR)
    c.line(0, 46, WIN_W, 46)
    c.text(WIN_W / 2, 23, "File Library", 14, TEXT, bold=True, anchor="mm")
    c.ellipse(958, 12, 980, 34, fill="#d6d6d6")
    c.line(965, 19, 973, 27, fill="#444444", width=1.5)
    c.line(973, 19, 965, 27, fill="#444444", width=1.5)

    # toolbar
    c.rect(0, 47, WIN_W, 92, fill=TOOL)
    button(c, 12, 54, 112, "Add folder", icon_add_folder)
    button(c, 130, 54, 112, "Rescan all", lambda c_, x, y: icon_refresh(c_, x, y + 1, "#8a8a8a", 15))
    c.line(254, 56, 254, 84)
    button(c, 266, 54, 120, "Save config", icon_save)
    button(c, 392, 54, 112, "Export list", icon_export)
    button(c, 890, 54, 98, "About", icon_info)
    c.line(0, 92, WIN_W, 92)
    c.line(0, 120, WIN_W, 120)

    # left panel: four folders, one file type each (chips wrap onto two lines)
    c.line(310, 120, 310, status_y)
    c.text(12, 136, "Folders and file types", 11, DIM)
    y = 152
    for name, path, kind in FOLDERS:
        c.text(14, y + 18, name, 13)
        c.text(14, y + 38, path, 10.5, DIM)
        cx, cy = 14, y + 52
        for key, label in TYPE_LABELS:
            w = c.width(label, 11) + 20
            if cx + w > 14 + 204:
                cx, cy = 14, cy + 27
            chip(c, cx, cy, label, key == kind)
            cx += w + 5
        icon_eye(c, 226, y + 13)
        icon_refresh(c, 254, y + 13)
        icon_trash(c, 282, y + 13)
        c.line(0, y + 116, 310, y + 116)
        y += 116

    # search row (empty search, both options off)
    c.rect(323, 130, 540, 162, fill="#ffffff", outline="#b5b5b5", r=6)
    icon_search(c, 334, 138)
    c.text(358, 146, "Search file names", 12, "#9a9a9a")
    checkbox(c, 556, 138, False)
    c.text(578, 146, "Case sensitive", 12.5)
    checkbox(c, 684, 138, False)
    c.text(706, 146, "Ignore delimiter", 12.5)
    checkbox(c, 822, 138, False)
    c.text(844, 146, "Ignore special chars", 12.5)

    # list
    tree_bottom = status_y - 40
    c.rect(323, 172, 988, tree_bottom, fill="#ffffff", outline="#cfcfcf", r=6)
    ry = 186
    total_mb, nfiles = 0.0, 0
    for depth, kind, name, size in TREE:
        x = 336 + depth * 22
        if kind == "dir":
            c.poly([(x, ry - 3), (x + 8, ry - 3), (x + 4, ry + 3)], "#888888")
            icon_folder(c, x + 14, ry - 8)
            c.text(x + 36, ry, name, 13, bold=True)
        else:
            nfiles += 1
            total_mb += size
            KIND_ICON[kind](c, x + 14, ry - 7)
            c.text(x + 36, ry, name, 13)
            c.text(972, ry, f"{size:.2f} MB", 12.5, "#555555", anchor="rm")
        ry += 26

    # bottom row: hint on the left, type filter on the right (all four shown)
    row_y = status_y - 20
    c.text(323, row_y, "Right-click a file, or select it and press F1 to F4.", 10.5, DIM)
    widths = [c.width(label, 11) + 20 for _, label in TYPE_LABELS]
    x = 988 - (sum(widths) + 5 * (len(widths) - 1))
    c.text(x - 8, row_y, "Show:", 11, DIM, anchor="rm")
    for (key, label), w in zip(TYPE_LABELS, widths):
        chip(c, x, row_y - 11, label, True)
        x += w + 5

    # status bar
    c.d.rounded_rectangle([c.p(0), c.p(status_y), c.p(WIN_W), c.p(WIN_H)], radius=12 * S, fill=TOOL)
    c.rect(0, status_y, WIN_W, status_y + 16, fill=TOOL)
    c.line(0, status_y, WIN_W, status_y)
    size_txt = f"{total_mb / 1024:.2f} GB" if total_mb >= 1024 else f"{total_mb:.1f} MB"
    c.text(12, status_y + 18, f"{nfiles} files \u00b7 {size_txt} shown", 12, "#555555")
    c.text(988, status_y + 18, "Cache updated today, 09:14", 12, "#555555", anchor="rm")

    out = c.img.resize((c.w // 2, c.h // 2), Image.LANCZOS)
    os.makedirs("docs", exist_ok=True)
    out.save("docs/screenshot.png", optimize=True)
    print("docs/screenshot.png written", out.size)


if __name__ == "__main__":
    render()
