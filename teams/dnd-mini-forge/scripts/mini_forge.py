#!/usr/bin/env python3
"""
mini_forge.py: turn a Sloyd GLB into a print-ready tabletop miniature or terrain piece.

  mini     scale a figure to 28mm/32mm heroic scale, put it on a round base, export STL
  terrain  scale scatter terrain to the same table scale, flatten its bottom, export STL(s)
  sizes    print the D&D size-category -> base-size table and the race height table

Scale model: 1 inch of battle grid = 5 ft. 28mm heroic ~ 1:60 (5.08 mm per ft), 32mm heroic
~ 1:54 (5.64 mm per ft). A 6 ft human is ~30.5 mm tall at 28mm (eye level ~28 mm) and ~34 mm at 32mm.

Requires: pip install trimesh numpy manifold3d scipy
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

try:
    import numpy as np
    import trimesh
except ImportError:  # pragma: no cover
    sys.exit("mini_forge.py needs trimesh + numpy: pip install trimesh numpy manifold3d scipy")

MM_PER_FT = {"28": 304.8 / 60.0, "32": 304.8 / 54.0}

# D&D 5e size categories -> grid space (ft) and the standard round base (mm).
# Bases are chosen to sit inside 1"/2"/3"/4" grid squares (25.4 mm per square).
SIZES = {
    "tiny":       {"space_ft": 2.5, "base_mm": 25, "alt": "20 mm if you want 4 per square"},
    "small":      {"space_ft": 5,   "base_mm": 25, "alt": ""},
    "medium":     {"space_ft": 5,   "base_mm": 25, "alt": "32 mm for 32mm-scale collections (overhangs a 1\" square)"},
    "large":      {"space_ft": 10,  "base_mm": 50, "alt": "40 mm for slim Large creatures"},
    "huge":       {"space_ft": 15,  "base_mm": 75, "alt": "60 mm in tight dungeons"},
    "gargantuan": {"space_ft": 20,  "base_mm": 100, "alt": "120 mm+ for dragons and colossi"},
}

# Typical standing height in feet (adult, upright). Used when --height-ft is not given.
RACE_HEIGHT_FT = {
    "human": 5.9, "elf": 5.6, "half-elf": 5.7, "drow": 5.3, "dwarf": 4.4, "halfling": 3.0,
    "gnome": 3.4, "half-orc": 6.2, "orc": 6.2, "tiefling": 5.9, "aasimar": 5.9,
    "dragonborn": 6.4, "goliath": 7.5, "firbolg": 7.5, "tabaxi": 5.9, "kenku": 5.0,
    "aarakocra": 5.0, "tortle": 5.5, "lizardfolk": 5.9, "warforged": 6.2, "genasi": 5.9,
    "githyanki": 6.0, "goblin": 3.5, "hobgoblin": 5.9, "bugbear": 7.0, "kobold": 2.5,
    "triton": 5.4, "yuan-ti": 5.9, "minotaur": 7.0, "centaur": 7.0, "changeling": 5.8,
    "owlin": 4.8, "harengon": 5.0, "satyr": 5.2, "fairy": 2.0, "loxodon": 7.5,
}

# Base height (mm) and bevel (mm) per diameter, close to common GW/Litko bases.
def base_dims(d: float) -> tuple[float, float]:
    if d <= 25:
        return 3.2, 0.9
    if d <= 32:
        return 3.6, 1.0
    if d <= 40:
        return 4.0, 1.2
    if d <= 60:
        return 4.5, 1.4
    return 5.0, 1.6


# ----------------------------------------------------------------------------- loading

def load_mesh(path: Path, up: str) -> tuple[trimesh.Trimesh, list[trimesh.Trimesh]]:
    """Load a GLB/GLTF/OBJ/STL, bake scene transforms, return (combined, parts) in Z-up."""
    loaded = trimesh.load(str(path), force="scene")
    parts = [g for g in loaded.dump() if isinstance(g, trimesh.Trimesh) and len(g.faces)]
    if not parts:
        sys.exit(f"{path}: no triangle meshes found")
    if up == "auto":
        up = "y" if path.suffix.lower() in (".glb", ".gltf") else "z"
    if up == "y":  # glTF is Y-up, front = +Z. Rotate +90 deg about X: Y->Z, front -> -Y (slicer front).
        rot = trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])
        for p in parts:
            p.apply_transform(rot)
    clean = []
    for p in parts:
        p = p.copy()
        p.merge_vertices()
        p.update_faces(p.nondegenerate_faces())
        p.remove_unreferenced_vertices()
        if len(p.faces):
            clean.append(p)
    combined = trimesh.util.concatenate(clean)
    return combined, clean


def drop_specks(mesh: trimesh.Trimesh, min_mm: float) -> tuple[trimesh.Trimesh, int]:
    """Remove disconnected bodies smaller than min_mm (bbox diagonal). AI meshes often carry
    floating crumbs that become failed supports or loose bits on the build plate."""
    bodies = mesh.split(only_watertight=False)
    if len(bodies) <= 1:
        return mesh, 0
    keep = [b for b in bodies if np.linalg.norm(b.extents) >= min_mm]
    dropped = len(bodies) - len(keep)
    if not keep:
        return mesh, 0
    return trimesh.util.concatenate(keep), dropped


def foot_center(mesh: trimesh.Trimesh, frac: float = 0.08) -> tuple[np.ndarray, np.ndarray]:
    """XY center and XY extents of the lowest slice (feet / hooves / tail tip). Centering on
    the feet instead of the bounding box keeps a mini with an out-thrust sword balanced."""
    z0, z1 = mesh.bounds[0][2], mesh.bounds[1][2]
    pts = mesh.vertices[mesh.vertices[:, 2] <= z0 + (z1 - z0) * frac][:, :2]
    if len(pts) < 3:
        pts = mesh.vertices[:, :2]
    lo, hi = pts.min(0), pts.max(0)
    return (lo + hi) / 2.0, hi - lo


# ----------------------------------------------------------------------------- base

def make_base(diameter: float, magnet: tuple[float, float] | None, hollow: bool,
              sections: int = 128) -> trimesh.Trimesh:
    """Revolve a closed (radius, z) profile into a watertight round base with a beveled rim,
    an optional magnet recess underneath, or an optional hollow underside for big bases."""
    h, bevel = base_dims(diameter)
    r_bot, r_top, lip = diameter / 2.0, diameter / 2.0 - bevel, 0.5
    if hollow:
        roof, wall = 1.6, 2.0
        r_in = r_bot - wall
        prof = [(0, h - roof), (r_in, h - roof), (r_in, 0), (r_bot, 0), (r_bot, lip), (r_top, h), (0, h)]
    elif magnet:
        md, mh = magnet
        rm = md / 2.0 + 0.1  # 0.2 mm clearance on diameter for press fit + glue
        prof = [(0, mh + 0.1), (rm, mh + 0.1), (rm, 0), (r_bot, 0), (r_bot, lip), (r_top, h), (0, h)]
    else:
        prof = [(0, 0), (r_bot, 0), (r_bot, lip), (r_top, h), (0, h)]
    base = trimesh.creation.revolve(np.array(prof, dtype=float), sections=sections)
    base.merge_vertices()
    base.fix_normals()
    if base.volume < 0:
        base.invert()
    return base


def union_or_merge(a: trimesh.Trimesh, b: trimesh.Trimesh) -> tuple[trimesh.Trimesh, str]:
    """Boolean-union when both are closed solids; otherwise keep overlapping shells.
    Every common slicer (Chitubox, Lychee, PrusaSlicer, Cura, Bambu Studio) merges
    overlapping shells, so the fallback still prints as one piece."""
    if a.is_watertight and b.is_watertight:
        try:
            u = trimesh.boolean.union([a, b], engine="manifold")
            if isinstance(u, trimesh.Trimesh) and len(u.faces) and u.is_watertight:
                return u, "boolean-union"
        except Exception:
            pass
    return trimesh.util.concatenate([a, b]), "merged-shells"


def try_repair(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    m = mesh.copy()
    trimesh.repair.fix_normals(m)
    trimesh.repair.fill_holes(m)
    return m


# ----------------------------------------------------------------------------- reports

def print_report(report: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, indent=2))
        return
    for k, v in report.items():
        if k == "warnings":
            continue
        print(f"{k:>18}: {v}")
    for w in report.get("warnings", []):
        print(f"  WARNING: {w}")


def solid_stats(mesh: trimesh.Trimesh) -> dict:
    out = {"triangles": int(len(mesh.faces)), "watertight": bool(mesh.is_watertight),
           "bodies": int(len(mesh.split(only_watertight=False)))}
    if mesh.is_watertight and mesh.volume > 0:
        ml = mesh.volume / 1000.0
        out["solid_volume_ml"] = round(ml, 2)
        out["resin_estimate_ml"] = round(ml * 1.15, 2)  # +15% supports and raft
        out["pla_estimate_g"] = round(ml * 1.24 * 0.6, 1)  # ~60% effective at 2 walls + 15% infill
    return out


# ----------------------------------------------------------------------------- commands

def cmd_mini(a: argparse.Namespace) -> int:
    src = Path(a.input)
    fig, _ = load_mesh(src, a.up)
    warnings: list[str] = []

    size = a.size.lower()
    base_d = a.base if a.base else SIZES[size]["base_mm"]
    mmft = MM_PER_FT[a.scale]

    if a.height_mm:
        target, how = a.height_mm, "explicit --height-mm"
    elif a.fit == "footprint":
        target, how = None, f"footprint = {a.footprint_ratio:.2f} x {base_d} mm base"
    else:
        ft = a.height_ft or RACE_HEIGHT_FT.get((a.race or "human").lower())
        if ft is None:
            sys.exit(f"unknown race '{a.race}'. Pass --height-ft or one of: {', '.join(sorted(RACE_HEIGHT_FT))}")
        ft *= a.pose_factor
        target, how = ft * mmft, f"{ft:.2f} ft x {mmft:.2f} mm/ft ({a.scale}mm heroic)"

    if target is not None:
        s = target / fig.extents[2]
    else:
        xy = max(fig.extents[0], fig.extents[1])
        s = (base_d * a.footprint_ratio) / xy
    fig.apply_scale(s)

    fig, dropped = drop_specks(fig, a.min_part_mm)
    if dropped:
        warnings.append(f"removed {dropped} floating speck(s) under {a.min_part_mm} mm")

    c, feet = foot_center(fig)
    fig.apply_translation([-c[0], -c[1], 0])

    report = {"input": str(src), "scale": f"{a.scale}mm heroic (1:{304.8 / mmft:.0f})",
              "sizing": how, "figure_height_mm": round(float(fig.extents[2]), 2)}

    if a.no_base:
        fig.apply_translation([0, 0, -fig.bounds[0][2]])
        out = fig
        report["base"] = "none"
    else:
        hollow = a.hollow_base or (a.hollow_base is None and base_d >= 50 and not a.magnet)
        magnet = None
        if a.magnet and not hollow:
            md, mh = (float(x) for x in a.magnet.lower().split("x"))
            magnet = (md, mh)
        base = make_base(base_d, magnet, hollow)
        bh, bevel = base_dims(base_d)
        lift = a.flight_stand or 0.0
        fig.apply_translation([0, 0, bh + lift - a.sink - fig.bounds[0][2]])
        if lift:
            # Flying creature: a tapered post from the base into the belly at the lowest point.
            low = fig.vertices[np.argmin(fig.vertices[:, 2])]
            r = 1.6 if base_d <= 32 else 2.5 if base_d <= 60 else 3.5
            post = trimesh.creation.cylinder(radius=r, height=lift + a.sink + 2.0, sections=48)
            post.apply_translation([low[0], low[1], bh - 0.5 + (lift + a.sink + 2.0) / 2])
            base, _ = union_or_merge(base, post)
            report["flight_stand_mm"] = lift
        r_top = base_d / 2 - bevel
        if max(feet) / 2 > r_top:
            warnings.append(f"feet span {max(feet):.1f} mm, wider than the {2 * r_top:.1f} mm base top; "
                            f"use a bigger --base or --fit footprint")
        reach = float(np.max(np.linalg.norm(fig.vertices[:, :2], axis=1)))
        if reach > base_d / 2 * 1.45:
            warnings.append(f"model reaches {reach:.1f} mm from center (base radius {base_d / 2:.0f}); "
                            f"overhanging capes/weapons tip easily and snag supports")
        if not fig.is_watertight and a.repair:
            fig = try_repair(fig)
        out, mode = union_or_merge(fig, base)
        report["base"] = (f"{base_d} mm round, {bh} mm tall"
                          + (f", magnet recess {a.magnet} mm" if magnet else "")
                          + (", hollow underside" if hollow else ""))
        report["join"] = mode
        if mode == "merged-shells":
            warnings.append("figure mesh is not closed, so it was placed into the base as an overlapping "
                            "shell (slicers merge this). Run your slicer's repair if it reports errors")

    if fig.extents[2] < 18 and not a.no_base:
        warnings.append("figure under 18 mm tall: faces and hands will be mush on FDM, use resin")

    report.update({"overall_mm": [round(float(x), 2) for x in out.extents]})
    report.update(solid_stats(out))

    dst = Path(a.output)
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.export(str(dst))
    report["stl"] = str(dst)
    if a.glb_out:
        scene_out = out.copy()
        scene_out.export(str(a.glb_out))
        report["glb"] = str(a.glb_out)
    report["warnings"] = warnings
    print_report(report, a.json)
    return 0


def flatten_bottom(mesh: trimesh.Trimesh, cut_mm: float) -> tuple[trimesh.Trimesh, bool]:
    if cut_mm <= 0:
        return mesh, False
    z = mesh.bounds[0][2] + cut_mm
    try:
        cut = mesh.slice_plane([0, 0, z], [0, 0, 1], cap=mesh.is_watertight)
        if cut is not None and len(cut.faces):
            return cut, True
    except Exception:
        pass
    return mesh, False


def cmd_terrain(a: argparse.Namespace) -> int:
    src = Path(a.input)
    combined, parts = load_mesh(src, a.up)
    mmft = MM_PER_FT[a.scale]
    warnings: list[str] = []

    if a.height_ft:
        s = a.height_ft * mmft / combined.extents[2]
        how = f"height {a.height_ft} ft"
    elif a.footprint_ft:
        s = a.footprint_ft * mmft / max(combined.extents[0], combined.extents[1])
        how = f"footprint {a.footprint_ft} ft"
    else:
        sys.exit("terrain needs --height-ft or --footprint-ft so the whole set shares one scale")

    # One transform for the whole model, so split parts still fit together.
    T = np.eye(4)
    T[:3, :3] *= s
    combined.apply_transform(T)
    lo = combined.bounds[0]
    center = (combined.bounds[0] + combined.bounds[1]) / 2
    shift = [-center[0], -center[1], -lo[2]]
    combined.apply_translation(shift)

    dst = Path(a.output)
    report = {"input": str(src), "scale": f"{a.scale}mm (1:{304.8 / mmft:.0f}, 1 in grid = 5 ft)",
              "sizing": how, "overall_mm": [round(float(x), 2) for x in combined.extents],
              "grid_squares": [round(float(combined.extents[0]) / 25.4, 2), round(float(combined.extents[1]) / 25.4, 2)]}

    if a.parts and len(parts) > 1:
        dst.mkdir(parents=True, exist_ok=True)
        files = []
        for i, p in enumerate(parts):
            p = p.copy()
            p.apply_transform(T)
            p.apply_translation(shift)
            p, _ = drop_specks(p, a.min_part_mm)
            if np.linalg.norm(p.extents) < a.min_part_mm:
                continue
            if a.lay_flat:
                p.apply_translation([0, 0, -p.bounds[0][2]])
            f = dst / f"{src.stem}_part{i + 1:02d}.stl"
            p.export(str(f))
            files.append({"file": f.name, "mm": [round(float(x), 1) for x in p.extents],
                          "watertight": bool(p.is_watertight)})
        report["parts"] = files
        report["note"] = "parts keep their assembled position (z=0 is the table) unless --lay-flat"
    else:
        if a.parts:
            warnings.append("model has a single mesh; exporting one piece")
        combined, dropped = drop_specks(combined, a.min_part_mm)
        combined, flat = flatten_bottom(combined, a.flatten)
        combined.apply_translation([0, 0, -combined.bounds[0][2]])
        if flat:
            report["flattened"] = f"bottom {a.flatten} mm cut flat"
        if dst.suffix.lower() != ".stl":
            dst.mkdir(parents=True, exist_ok=True)
            dst = dst / f"{src.stem}.stl"
        dst.parent.mkdir(parents=True, exist_ok=True)
        combined.export(str(dst))
        report.update(solid_stats(combined))
        report["stl"] = str(dst)

    if combined.extents[2] < 5:
        warnings.append("piece is under 5 mm tall at this scale; check the height you passed")
    report["warnings"] = warnings
    print_report(report, a.json)
    return 0


def cmd_sizes(a: argparse.Namespace) -> int:
    if a.json:
        print(json.dumps({"sizes": SIZES, "race_height_ft": RACE_HEIGHT_FT,
                          "mm_per_ft": MM_PER_FT}, indent=2))
        return 0
    print("size         space   base    alternative")
    for k, v in SIZES.items():
        print(f"{k:<12} {v['space_ft']:>4} ft  {v['base_mm']:>3} mm   {v['alt']}")
    print("\nheights at 28mm / 32mm (standing):")
    for r, ft in sorted(RACE_HEIGHT_FT.items(), key=lambda x: x[1]):
        print(f"  {r:<11} {ft:>4.1f} ft  {ft * MM_PER_FT['28']:5.1f} mm  {ft * MM_PER_FT['32']:5.1f} mm")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("mini", help="figure -> scaled mini on a round base (STL)")
    m.add_argument("input")
    m.add_argument("-o", "--output", required=True, help="output .stl")
    m.add_argument("--scale", choices=["28", "32"], default="28")
    m.add_argument("--race", help="pick a standard height, e.g. dwarf, halfling, goliath")
    m.add_argument("--height-ft", type=float, help="creature standing height in feet")
    m.add_argument("--height-mm", type=float, help="final figure height in mm (overrides scale)")
    m.add_argument("--pose-factor", type=float, default=1.0,
                   help="model height / standing height: 1.15 if a weapon is raised above the head, "
                        "0.8 crouching, 1.3 with wings up")
    m.add_argument("--size", choices=list(SIZES), default="medium", help="D&D size category -> base")
    m.add_argument("--base", type=float, help="base diameter mm (overrides --size)")
    m.add_argument("--fit", choices=["height", "footprint"], default="height",
                   help="footprint: scale so the creature's length fills the base (beasts, dragons)")
    m.add_argument("--footprint-ratio", type=float, default=1.0)
    m.add_argument("--magnet", help="magnet recess under the base, e.g. 6x2 or 8x3 (mm)")
    m.add_argument("--hollow-base", action="store_true", default=None,
                   help="hollow underside (default on for bases >= 50 mm without magnet)")
    m.add_argument("--solid-base", dest="hollow_base", action="store_false")
    m.add_argument("--no-base", action="store_true", help="figure only, feet on z=0")
    m.add_argument("--sink", type=float, default=0.8, help="mm the feet sink into the base")
    m.add_argument("--flight-stand", type=float, metavar="MM",
                   help="lift a flyer this many mm on a printed post (dragons, harpies, beholders)")
    m.add_argument("--min-part-mm", type=float, default=1.0, help="drop floating bits smaller than this")
    m.add_argument("--no-repair", dest="repair", action="store_false")
    m.add_argument("--glb-out", help="also write the scaled print model as GLB (preview / VTT)")
    m.add_argument("--up", choices=["auto", "y", "z"], default="auto")
    m.add_argument("--json", action="store_true")
    m.set_defaults(func=cmd_mini)

    t = sub.add_parser("terrain", help="scatter terrain -> table scale STL (or one STL per part)")
    t.add_argument("input")
    t.add_argument("-o", "--output", required=True, help="output .stl, or a folder with --parts")
    t.add_argument("--scale", choices=["28", "32"], default="28")
    t.add_argument("--height-ft", type=float, help="real height of the object in feet")
    t.add_argument("--footprint-ft", type=float, help="real longest side in feet")
    t.add_argument("--parts", action="store_true", help="export each mesh (from split_model_into_parts)")
    t.add_argument("--lay-flat", action="store_true", help="drop every part to z=0")
    t.add_argument("--flatten", type=float, default=0.4, help="mm cut off the bottom so it sits flat")
    t.add_argument("--min-part-mm", type=float, default=1.0)
    t.add_argument("--up", choices=["auto", "y", "z"], default="auto")
    t.add_argument("--json", action="store_true")
    t.set_defaults(func=cmd_terrain)

    s = sub.add_parser("sizes", help="size categories, base sizes and race heights")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_sizes)

    a = p.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
