#!/usr/bin/env python3
"""
render_preview.py: quick grey-resin preview render of an STL/GLB, no GPU or Blender needed.

  python render_preview.py mini.stl -o mini.png                  # 3/4 hero shot
  python render_preview.py mini.stl -o mini.gif --turntable 36   # turntable GIF
  python render_preview.py a.stl b.stl c.stl -o party.png        # line-up, shared scale

Flat-shaded painter's-algorithm renderer (PIL + numpy). Good enough to check pose, scale and
base before slicing, and for share images. Models are expected Z-up in mm (mini_forge.py output).
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BG_TOP, BG_BOTTOM = (18, 35, 74), (2, 18, 37)  # Sloyd navy #12234a -> #021225
RESIN = np.array([168, 176, 186], dtype=float)


def load(path: Path) -> trimesh.Trimesh:
    m = trimesh.load(str(path), force="mesh")
    if path.suffix.lower() in (".glb", ".gltf"):
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    return m


def background(w: int, h: int) -> Image.Image:
    t = np.linspace(0, 1, h)[:, None]
    top, bot = np.array(BG_TOP, float), np.array(BG_BOTTOM, float)
    rows = (top * (1 - t) + bot * t).astype(np.uint8)
    img = np.repeat(rows[:, None, :], w, axis=1).reshape(h, w, 3)
    return Image.fromarray(img, "RGB")


def view_matrix(azim_deg: float, elev_deg: float) -> np.ndarray:
    az, el = math.radians(azim_deg), math.radians(elev_deg)
    rz = np.array([[math.cos(az), -math.sin(az), 0], [math.sin(az), math.cos(az), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, math.cos(el), -math.sin(el)], [0, math.sin(el), math.cos(el)]])
    # camera looks along +Y (model front faces -Y), screen x = X, screen up = Z
    return rx @ rz


def draw_meshes(img: Image.Image, meshes: list[trimesh.Trimesh], offsets: list[float],
                azim: float, elev: float, scale_px: float, cx: float, cy: float) -> None:
    R = view_matrix(azim, elev)
    light = np.array([-0.45, -0.75, 0.55])
    light /= np.linalg.norm(light)
    polys, depth, colors = [], [], []
    for m, dx in zip(meshes, offsets):
        v = (m.vertices - [0, 0, 0]) @ R.T
        v[:, 0] += dx
        tri = v[m.faces]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        ln[ln == 0] = 1
        n /= ln
        facing = n[:, 1] < 0  # toward camera at -Y
        n_vis = np.where(facing[:, None], n, -n)
        lam = np.clip(n_vis @ light, 0, 1)
        rim = np.clip(1 - np.abs(n_vis[:, 1]), 0, 1) ** 3
        shade = 0.28 + 0.62 * lam + 0.25 * rim
        col = np.clip(RESIN[None, :] * shade[:, None], 0, 255)
        polys.append(tri)
        depth.append(tri[:, :, 1].mean(1))
        colors.append(col)
    tri = np.concatenate(polys)
    d = np.concatenate(depth)
    col = np.concatenate(colors).astype(np.uint8)
    order = np.argsort(-d)  # far (large y) first
    sx = cx + tri[:, :, 0] * scale_px
    sy = cy - tri[:, :, 2] * scale_px
    draw = ImageDraw.Draw(img)
    for i in order:
        c = tuple(int(x) for x in col[i])
        draw.polygon([(sx[i, 0], sy[i, 0]), (sx[i, 1], sy[i, 1]), (sx[i, 2], sy[i, 2])], fill=c, outline=c)


def frame(meshes, offsets, span_x, span_z, z_mid, w, h, azim, elev, ss, title, font_path):
    W, H = w * ss, h * ss
    img = background(W, H)
    margin = 0.80 if not title else 0.72
    scale_px = min(W * 0.86 / span_x, H * margin / span_z)
    cy = H * (0.52 if not title else 0.58) + z_mid * scale_px
    # soft contact shadow
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).ellipse([W * 0.5 - span_x * scale_px * 0.55, cy - 14 * ss,
                                W * 0.5 + span_x * scale_px * 0.55, cy + 22 * ss], fill=120)
    sh = sh.filter(ImageFilter.GaussianBlur(18 * ss))
    img.paste((0, 0, 0), (0, 0), sh)
    draw_meshes(img, meshes, offsets, azim, elev, scale_px, W / 2, cy)
    img = img.resize((w, h), Image.LANCZOS)
    if title:
        d = ImageDraw.Draw(img)
        try:
            f = ImageFont.truetype(font_path, int(h * 0.045)) if font_path else ImageFont.load_default(int(h * 0.045))
        except Exception:
            f = ImageFont.load_default()
        tw = d.textlength(title, font=f)
        d.text(((w - tw) / 2, h * 0.05), title, fill=(255, 255, 255), font=f)
    return img


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("inputs", nargs="+")
    p.add_argument("-o", "--output", required=True, help=".png or .gif")
    p.add_argument("--size", default="1080x1350", help="WxH, default 1080x1350 (4:5)")
    p.add_argument("--azim", type=float, default=-28)
    p.add_argument("--elev", type=float, default=14)
    p.add_argument("--turntable", type=int, default=0, help="frames for a 360 GIF")
    p.add_argument("--title", default="")
    p.add_argument("--font", help="TTF path, e.g. Poppins-SemiBold.ttf")
    p.add_argument("--max-faces", type=int, default=120000, help="decimate previews above this")
    p.add_argument("--ss", type=int, default=2, help="supersampling")
    a = p.parse_args()

    w, h = (int(x) for x in a.size.lower().split("x"))
    meshes = []
    for f in a.inputs:
        m = load(Path(f))
        if len(m.faces) > a.max_faces:
            try:
                m = m.simplify_quadric_decimation(face_count=a.max_faces)
            except Exception:
                pass
        c = (m.bounds[0] + m.bounds[1]) / 2
        m.apply_translation([-c[0], -c[1], -m.bounds[0][2]])
        meshes.append(m)

    gap = 6.0
    widths = [max(m.extents[0], m.extents[1]) for m in meshes]
    total = sum(widths) + gap * (len(meshes) - 1)
    offsets, x = [], -total / 2
    for wd in widths:
        offsets.append(x + wd / 2)
        x += wd + gap
    span_x = total * 1.05
    span_z = max(m.extents[2] for m in meshes) * 1.12
    z_mid = span_z / 2 * 0.9

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if a.turntable and out.suffix.lower() == ".gif":
        frames = [frame(meshes, offsets, span_x, span_z, z_mid, w, h, a.azim + i * 360 / a.turntable,
                        a.elev, a.ss, a.title, a.font) for i in range(a.turntable)]
        frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(4000 / a.turntable),
                       loop=0, optimize=True)
    else:
        frame(meshes, offsets, span_x, span_z, z_mid, w, h, a.azim, a.elev, a.ss, a.title, a.font).save(out)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
