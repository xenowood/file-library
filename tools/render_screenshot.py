#!/usr/bin/env python3
"""Render docs/screenshot.png: an illustration of the File Library main window.

This is drawn with Pillow from sample data, it is not a capture of the real
application. Replace docs/screenshot.png with a real screenshot when you like.

Needs Pillow (python3-pil) and the DejaVu Sans fonts. Run from the project root:
    python3 tools/render_screenshot.py
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import file_library_core as core  # noqa: E402

S = 4                      # drawing scale, downsampled to 2x at the end
WIN_W, WIN_H = 1000, 640   # logical window size
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
CHIP_ON_BG, CHIP_ON_FG, CHIP_ON_BORDER = "#d9e8fb", "#1c5fb8", "#a9c9f2"
HILITE = "#f5d76e"
FOLDER_Y = "#e5a50a"
VIDEO_C, IMAGE_C, DOC_C = "#2f6fdd", "#2fa36b", "#f08a24"

QUERY = "the time has come"

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


KIND_ICON = {"v": icon_video, "i": icon_image, "d": icon_doc}


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


def highlighted(c, x, y, name, size=13):
    """Draw a file name with the search match highlighted (extension ignored)."""
    span = core.find_in_filename(name, QUERY, False, True)
    i, j = span if span else (0, 0)
    cx = x
    for text, hit in ((name[:i], False), (name[i:j], True), (name[j:], False)):
        if not text:
            continue
        w = c.width(text, size)
        if hit:
            c.rect(cx - 0.5, y - 9, cx + w + 0.5, y + 9, fill=HILITE, r=2)
        c.text(cx, y, text, size, "#000000" if hit else TEXT)
        cx += w


# ------------------------------------------------------------------ data
FOLDERS = [
    ("Videos", "/home/user/Videos", True, {"v", "i"}),
    ("Movies", "/mnt/media/Movies", True, {"v"}),
    ("Documents", "/home/user/Documents", True, {"d"}),
]
# (depth, kind, name, size_mb); kind "dir" rows have no size
TREE = [
    (0, "dir", "Videos", None),
    (1, "v", "the_time_has_come.mov", 356.71),
    (1, "dir", "Concerts", None),
    (2, "v", "The-Time-Has-Come.avi", 87.40),
    (2, "v", "the.time.has.come (live).mkv", 1204.88),
    (0, "dir", "Movies", None),
    (1, "v", "the time has come.mp4", 812.55),
    (1, "dir", "Trailers", None),
    (2, "v", "the,time,has,come - trailer.mp4", 42.10),
    (0, "dir", "Documents", None),
    (1, "d", "the-time-has-come notes.pdf", 0.80),
]
MENU_ROW_NAME = "the time has come.mp4"


def render():
    c = Canvas()

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
    button(c, 392, 54, 112, "Export .txt", icon_export)
    button(c, 890, 54, 98, "About", icon_info)
    c.line(0, 92, WIN_W, 92)
    c.line(0, 120, WIN_W, 120)

    # left panel
    c.line(310, 120, 310, 604)
    c.text(12, 136, "Folders and file types", 11, DIM)
    y = 152
    for name, path, enabled, types in FOLDERS:
        checkbox(c, 14, y + 10, enabled)
        c.text(40, y + 18, name, 13)
        c.text(40, y + 38, path, 10.5, DIM)
        x = 40
        for key, label in (("v", "Videos"), ("i", "Images"), ("d", "Documents")):
            x = chip(c, x, y + 52, label, key in types)
        icon_refresh(c, 252, y + 10)
        icon_trash(c, 281, y + 10)
        c.line(0, y + 88, 310, y + 88)
        y += 88

    # search row
    c.rect(323, 130, 690, 162, fill="#ffffff", outline="#b5b5b5", r=6)
    icon_search(c, 334, 138)
    c.text(358, 146, QUERY, 13)
    checkbox(c, 706, 138, False)
    c.text(728, 146, "Case sensitive", 12.5)
    checkbox(c, 836, 138, True)
    c.text(858, 146, "Ignore delimiter", 12.5)

    # tree
    c.rect(323, 172, 988, 574, fill="#ffffff", outline="#cfcfcf", r=6)
    ry = 186
    total_mb, nfiles = 0.0, 0
    menu_anchor = None
    for depth, kind, name, size in TREE:
        x = 336 + depth * 22
        if kind == "dir":
            c.poly([(x, ry - 3), (x + 8, ry - 3), (x + 4, ry + 3)], "#888888")
            icon_folder(c, x + 14, ry - 8)
            c.text(x + 36, ry, name, 13, bold=True)
        else:
            nfiles += 1
            total_mb += size
            if name == MENU_ROW_NAME:
                c.rect(324, ry - 13, 987, ry + 13, fill="#d9e8fb")
                menu_anchor = (660, ry + 8)
            KIND_ICON[kind](c, x + 14, ry - 7)
            highlighted(c, x + 36, ry, name)
            c.text(972, ry, f"{size:.2f} MB", 12.5, "#555555", anchor="rm")
        ry += 26

    c.text(323, 590, "Right-click a file to copy its full path or open its folder.", 10.5, DIM)

    # context menu
    mx, my = menu_anchor
    sh = Image.new("RGBA", c.img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle(
        [c.p(mx), c.p(my + 3), c.p(mx + 204), c.p(my + 75)], radius=8 * S, fill=(0, 0, 0, 60))
    sh = sh.filter(ImageFilter.GaussianBlur(5 * S))
    c.img = Image.alpha_composite(c.img, sh)
    c.d = ImageDraw.Draw(c.img)
    c.rect(mx, my, mx + 204, my + 72, fill="#ffffff", outline="#c4c4c4", r=8)
    c.rect(mx + 4, my + 4, mx + 200, my + 34, fill="#eef1f5", r=5)
    c.text(mx + 14, my + 19, "Copy file path", 13)
    c.text(mx + 14, my + 53, "Open containing folder", 13)

    # status bar
    c.line(0, 604, WIN_W, 604)
    c.d.rounded_rectangle([c.p(0), c.p(604), c.p(WIN_W), c.p(WIN_H)], radius=12 * S, fill=TOOL)
    c.rect(0, 604, WIN_W, 620, fill=TOOL)
    c.line(0, 604, WIN_W, 604)
    size_txt = f"{total_mb / 1024:.2f} GB" if total_mb >= 1024 else f"{total_mb:.1f} MB"
    c.text(12, 622, f"{nfiles} files \u00b7 {size_txt} shown", 12, "#555555")
    c.text(988, 622, "Cache updated today, 09:14", 12, "#555555", anchor="rm")

    out = c.img.resize((c.w // 2, c.h // 2), Image.LANCZOS)
    os.makedirs("docs", exist_ok=True)
    out.save("docs/screenshot.png", optimize=True)
    print("docs/screenshot.png written", out.size)


if __name__ == "__main__":
    render()
