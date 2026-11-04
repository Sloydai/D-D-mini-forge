#!/usr/bin/env python3
"""
scene_tools.py: turn Sloyd images and skyboxes into table-ready battle maps and backdrops.

  grid      battle-map image -> VTT PNG at an exact pixels-per-square, optional grid overlay
  print     battle-map image -> 1-inch-grid pages (Letter/A4 PDF) to tape together at the table
  still     equirectangular skybox -> flat 16:9 view for a TV / second screen / VTT backdrop

Grid conventions: Foundry VTT default 100 px/square, Roll20 70 px, Owlbear Rodeo any (we use 100).
Printed grids are 1 inch (25.4 mm) per 5 ft square so 25 mm bases fit.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

PAGES = {"letter": (8.5, 11.0), "a4": (8.27, 11.69)}


def fit_to_grid(img: Image.Image, cols: int, rows: int, px: int) -> Image.Image:
    """Center-crop to the grid aspect, then resize so every square is exactly px pixels."""
    W, H = img.size
    target = cols / rows
    if W / H > target:
        nw = int(H * target)
        img = img.crop(((W - nw) // 2, 0, (W - nw) // 2 + nw, H))
    else:
        nh = int(W / target)
        img = img.crop((0, (H - nh) // 2, W, (H - nh) // 2 + nh))
    return img.resize((cols * px, rows * px), Image.LANCZOS)


def overlay_grid(img: Image.Image, px: int, alpha: int, color=(0, 0, 0)) -> Image.Image:
    img = img.convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w = max(1, px // 50)
    for x in range(0, img.size[0] + 1, px):
        d.line([(x, 0), (x, img.size[1])], fill=color + (alpha,), width=w)
    for y in range(0, img.size[1] + 1, px):
        d.line([(0, y), (img.size[0], y)], fill=color + (alpha,), width=w)
    return Image.alpha_composite(img, layer).convert("RGB")


def cmd_grid(a) -> int:
    img = Image.open(a.input).convert("RGB")
    out = fit_to_grid(img, a.cols, a.rows, a.px)
    if a.lines:
        out = overlay_grid(out, a.px, a.alpha)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    out.save(a.output)
    print(f"{a.output}: {a.cols}x{a.rows} squares at {a.px} px/square ({out.size[0]}x{out.size[1]} px). "
          f"In Foundry set Grid Size {a.px}; in Roll20 set the page to {a.cols}x{a.rows} units.")
    return 0


def cmd_print(a) -> int:
    dpi = a.dpi
    img = Image.open(a.input).convert("RGB")
    full = overlay_grid(fit_to_grid(img, a.cols, a.rows, dpi), dpi, a.alpha)  # 1 square = 1 inch
    pw, ph = PAGES[a.paper]
    margin = 0.25
    sq_x, sq_y = int(pw - 2 * margin), int(ph - 2 * margin)  # whole squares per page
    pages = []
    for r0 in range(0, a.rows, sq_y):
        for c0 in range(0, a.cols, sq_x):
            c1, r1 = min(c0 + sq_x, a.cols), min(r0 + sq_y, a.rows)
            tile = full.crop((c0 * dpi, r0 * dpi, c1 * dpi, r1 * dpi))
            page = Image.new("RGB", (int(pw * dpi), int(ph * dpi)), "white")
            page.paste(tile, (int(margin * dpi), int(margin * dpi)))
            d = ImageDraw.Draw(page)
            d.text((int(margin * dpi), int((ph - margin * 0.8) * dpi)),
                   f"rows {r0 + 1}-{r1}  cols {c0 + 1}-{c1}  (print at 100% / actual size)", fill="black")
            pages.append(page)
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(out, save_all=True, append_images=pages[1:], resolution=dpi)
    print(f"{out}: {len(pages)} {a.paper} page(s), {a.cols}x{a.rows} one-inch squares. Print at 100% scale.")
    return 0


def cmd_still(a) -> int:
    """Rectilinear (pinhole) view out of an equirectangular panorama."""
    pano = np.asarray(Image.open(a.input).convert("RGB"))
    H, W = pano.shape[:2]
    w, h = (int(x) for x in a.size.lower().split("x"))
    fov = math.radians(a.fov)
    f = (w / 2) / math.tan(fov / 2)
    xs, ys = np.meshgrid(np.arange(w) - w / 2 + 0.5, np.arange(h) - h / 2 + 0.5)
    dirs = np.stack([xs, -ys, np.full_like(xs, f)], -1)
    dirs /= np.linalg.norm(dirs, axis=-1, keepdims=True)
    yaw, pitch = math.radians(a.yaw), math.radians(a.pitch)
    cp, sp = math.cos(pitch), math.sin(pitch)
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    cy, sy = math.cos(yaw), math.sin(yaw)
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    d = dirs @ (ry @ rx).T
    lon = np.arctan2(d[..., 0], d[..., 2])
    lat = np.arcsin(np.clip(d[..., 1], -1, 1))
    u = ((lon / (2 * math.pi) + 0.5) * W).astype(int) % W
    v = np.clip(((0.5 - lat / math.pi) * H).astype(int), 0, H - 1)
    Image.fromarray(pano[v, u]).save(a.output)
    print(f"{a.output}: {w}x{h}, yaw {a.yaw}, pitch {a.pitch}, fov {a.fov}")
    return 0


def _trim_background(img: Image.Image, tol: int = 18) -> Image.Image:
    """Crop to the subject on a flat studio background (color sampled from the corners)."""
    a = np.asarray(img.convert("RGB")).astype(int)
    corners = np.array([a[0, 0], a[0, -1], a[-1, 0], a[-1, -1]])
    bg = np.median(corners, axis=0)
    mask = np.abs(a - bg).max(-1) > tol
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return img
    return img.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def cmd_token(a) -> int:
    """Round VTT token from a character concept: head-and-shoulders crop inside a colored ring."""
    img = _trim_background(Image.open(a.input).convert("RGB"))
    w, h = img.size
    side = int(min(w, h * a.crop))
    top = int(h * a.top)
    img = img.crop(((w - side) // 2, top, (w - side) // 2 + side, top + side)).resize((a.px, a.px), Image.LANCZOS)
    ring = max(4, a.px // 22)
    out = Image.new("RGBA", (a.px, a.px), (0, 0, 0, 0))
    m = Image.new("L", (a.px, a.px), 0)
    ImageDraw.Draw(m).ellipse([ring, ring, a.px - ring, a.px - ring], fill=255)
    out.paste(img, (0, 0), m)
    d = ImageDraw.Draw(out)
    col = tuple(int(a.ring[i:i + 2], 16) for i in (1, 3, 5))
    d.ellipse([ring // 2, ring // 2, a.px - ring // 2, a.px - ring // 2], outline=col + (255,), width=ring)
    out.save(a.output)
    print(f"{a.output}: {a.px}px token")
    return 0


def cmd_sheet(a) -> int:
    """Side-by-side contact sheet (concept -> turnaround -> render) with labels."""
    imgs = [Image.open(p).convert("RGB") for p in a.inputs]
    labels = (a.labels.split("|") if a.labels else [""] * len(imgs)) + [""] * len(imgs)
    h = a.height
    tiles = [im.resize((int(im.size[0] * h / im.size[1]), h), Image.LANCZOS) for im in imgs]
    pad, lab = 24, (54 if a.labels else 0)
    W = sum(t.size[0] for t in tiles) + pad * (len(tiles) + 1)
    sheet = Image.new("RGB", (W, h + 2 * pad + lab), (18, 35, 74))
    d = ImageDraw.Draw(sheet)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype(a.font, 30) if a.font else ImageFont.load_default(30)
    except Exception:
        from PIL import ImageFont
        font = ImageFont.load_default()
    x = pad
    for t, l in zip(tiles, labels):
        sheet.paste(t, (x, pad))
        if l:
            tw = d.textlength(l, font=font)
            d.text((x + (t.size[0] - tw) / 2, h + pad + 10), l, fill="white", font=font)
        x += t.size[0] + pad
    sheet.save(a.output)
    print(f"{a.output}: {sheet.size[0]}x{sheet.size[1]}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    tk = sub.add_parser("token", help="round VTT token from a character image")
    tk.add_argument("input"); tk.add_argument("-o", "--output", required=True)
    tk.add_argument("--px", type=int, default=400)
    tk.add_argument("--ring", default="#03f584", help="ring color hex (party color coding)")
    tk.add_argument("--crop", type=float, default=0.45, help="square side as fraction of figure height")
    tk.add_argument("--top", type=float, default=0.0, help="crop start as fraction of figure height")
    tk.set_defaults(func=cmd_token)

    sh = sub.add_parser("sheet", help="labelled contact sheet of images")
    sh.add_argument("inputs", nargs="+"); sh.add_argument("-o", "--output", required=True)
    sh.add_argument("--labels", help="'Concept|Side|Back|28mm STL'")
    sh.add_argument("--height", type=int, default=720); sh.add_argument("--font")
    sh.set_defaults(func=cmd_sheet)

    g = sub.add_parser("grid")
    g.add_argument("input"); g.add_argument("-o", "--output", required=True)
    g.add_argument("--cols", type=int, required=True); g.add_argument("--rows", type=int, required=True)
    g.add_argument("--px", type=int, default=100, help="pixels per square (Foundry 100, Roll20 70)")
    g.add_argument("--lines", action="store_true", help="burn grid lines in (most VTTs draw their own)")
    g.add_argument("--alpha", type=int, default=70)
    g.set_defaults(func=cmd_grid)

    pr = sub.add_parser("print")
    pr.add_argument("input"); pr.add_argument("-o", "--output", required=True, help=".pdf")
    pr.add_argument("--cols", type=int, required=True); pr.add_argument("--rows", type=int, required=True)
    pr.add_argument("--paper", choices=list(PAGES), default="letter")
    pr.add_argument("--dpi", type=int, default=150)
    pr.add_argument("--alpha", type=int, default=110)
    pr.set_defaults(func=cmd_print)

    s = sub.add_parser("still")
    s.add_argument("input"); s.add_argument("-o", "--output", required=True)
    s.add_argument("--yaw", type=float, default=0); s.add_argument("--pitch", type=float, default=0)
    s.add_argument("--fov", type=float, default=90); s.add_argument("--size", default="1920x1080")
    s.set_defaults(func=cmd_still)

    a = p.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
