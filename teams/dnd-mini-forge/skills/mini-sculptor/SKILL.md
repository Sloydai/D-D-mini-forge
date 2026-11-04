---
name: mini-sculptor
description: Turn a character turnaround (front plus side/back images) into a print-ready tabletop miniature STL using Sloyd generate_3d_from_images, then scale it to 28mm or 32mm heroic scale and add a 25/32/50 mm round base with a local script. Use when the user wants a 3D printable mini, an STL, or to resize or rebase a GLB, and for resin vs FDM print advice.
---

# Mini Sculptor

You are the sculptor and print tech. You take approved views from **character-designer** (or the
user's own images) and finish with an STL that drops straight into a slicer: true scale, centered
on a base, one solid piece, and a preview the user has seen.

Sloyd API rules: `${CLAUDE_PLUGIN_ROOT}/reference/sloyd-api.md`.
Printing guide: `${CLAUDE_PLUGIN_ROOT}/reference/printing-guide.md`.
Scale tables: `${CLAUDE_PLUGIN_ROOT}/reference/tabletop-scale.md`.

## 0. One-time setup of the local tools

```bash
python3 -m venv "${CLAUDE_PLUGIN_DATA}/venv" && "${CLAUDE_PLUGIN_DATA}/venv/bin/pip" install -q -r "${CLAUDE_PLUGIN_ROOT}/requirements.txt"
```

From here on, `PY="${CLAUDE_PLUGIN_DATA}/venv/bin/python"`. Skip setup if `$PY -c "import trimesh, manifold3d"` already works.

## 1. Inputs

- Best: `mini-forge/<slug>/character.json` from character-designer, with front, left and back URLs.
- User's own art: one front image works (`generate_3d_from_image`), but tell them a turnaround gives
  a cleaner back and sides. Offer character-designer to make the side and back views (30 credits).
- An existing GLB/OBJ/STL from anywhere: skip straight to step 3.

## 2. Sculpt (`generate_3d_from_images`, 30 credits)

Check the balance and state the cost first. Then call:

```json
{
  "frontImage": {"url": "<concept imageUrl>"},
  "leftImage":  {"url": "<left imageUrl>"},
  "backImage":  {"url": "<back imageUrl>"},
  "EnablePBR": "true",
  "FaceCount": "300000"
}
```

- `EnablePBR: "true"` adds a color texture (30 credits). Use it for the preview, VTT use and painting
  reference. If the user only wants a grey print, `"false"` is 20 credits.
- 300k faces is plenty for a 30 mm figure. At 500k or more, Sloyd charges +10 credits with no visible gain at this size.
- One image only: `generate_3d_from_image` with `file: {url}` and `targetFaceCount: 300000` (20 credits).

Poll `get_job` (`wait: 30`, usually 1-4 minutes) and download `outputs.glbUrl` to
`mini-forge/<slug>/<slug>.glb`. If the job fails, credits are refunded. Retry once. If it fails
again, the views probably disagree, so send them back to character-designer for that view.

## 3. Scale, base, STL (local, free)

```bash
$PY "${CLAUDE_PLUGIN_ROOT}/scripts/mini_forge.py" mini mini-forge/<slug>/<slug>.glb \
  -o mini-forge/<slug>/<slug>_28mm.stl --scale 28 --race dwarf --size medium --magnet 6x2 --json
```

Choose the flags:

| Flag | Use |
|---|---|
| `--scale 28` / `32` | 28 is D&D and WizKids standard. 32 matches modern GW. Keep the whole party on one scale. |
| `--race <race>` or `--height-ft 6.5` | true height. Race list: `mini_forge.py sizes` |
| `--pose-factor` | from character.json; 1.15 if a weapon is raised over the head |
| `--size small/medium/...` or `--base 32` | base diameter. Small and Medium are both 25 mm on a 1" grid |
| `--magnet 6x2` | magnet recess under the base (bases up to 40 mm) |
| `--glb-out x.glb` | scaled copy for VTTs that accept 3D (Foundry 3D Canvas, Tabletop Simulator) |
| `--no-base` | user wants to base it themselves |

What the script does:
1. Converts glTF Y-up to Z-up, so the front faces the slicer's front.
2. Removes floating specks under 1 mm.
3. Scales by height at the chosen scale.
4. Centers on the **feet**, not the bounding box, so an out-thrust sword doesn't push the mini off its base.
5. Sinks the feet 0.8 mm into a beveled round base.
6. Boolean-unions the figure and base into one watertight solid when the mesh is closed. Otherwise it keeps overlapping shells, which every slicer merges.
7. Reports resin and filament estimates and any warnings.

Act on warnings:
- "feet span ... wider than the base": use the next base up, or `--fit footprint`.
- "model reaches ... from center": a cape or weapon overhangs. It's fine for display, but warn that it tips.
- "under 18 mm tall": a halfling or gnome at 28mm. Recommend resin.

## 4. Preview and approve

```bash
$PY "${CLAUDE_PLUGIN_ROOT}/scripts/render_preview.py" mini-forge/<slug>/<slug>_28mm.stl -o mini-forge/<slug>/preview.png
```

Show the preview. Check that the figure stands upright, is centered on the base, and that the scale
looks right. For a share-ready turntable, add `--turntable 36` and write to a `.gif`.

## 5. Print advice (tailor it to the user's printer)

Ask "resin or FDM?" if you don't know. Give the 5 lines that matter from the printing guide, with numbers:

- **Resin:** tilt 30-45 deg back, no supports on the face, 0.05 mm layers, no hollowing under 40 mm,
  cure 2-4 min. Use the report's `resin_estimate_ml` for the resin needed.
- **FDM:** 0.2 mm nozzle if they have one, 0.08-0.12 mm layers, tree supports, 3-4 minis per plate
  for cooling, outer walls 30-50 mm/s.
- **Multicolor FDM:** the model must come from `genStyleId: "Color3DPrint"` art. Paint by region in the slicer.

## 6. Hand-off

Final files in `mini-forge/<slug>/`: `<slug>.glb` (textured source), `<slug>_28mm.stl`, `preview.png`
and the report JSON. Tell the user the STL path, the height in mm, the base size, and the print tips.
