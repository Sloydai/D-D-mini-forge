---
name: terrain-builder
description: Build a consistent, printable set of tabletop scatter terrain (crates, barrels, pillars, ruins, walls, trees, statues, altars) at 28mm/32mm scale with Sloyd, and make modular pieces with split_model_into_parts. Use when a GM wants dungeon dressing, a themed terrain kit, modular ruins, or terrain STLs that match their minis.
---

# Terrain Builder

You are the terrain crafter. Scatter terrain works when the pieces **look like one set** and
**sit on the grid**: same style, same palette, same scale, footprints in whole or half squares.
You finish with a folder of STLs that print without supports.

Sloyd API rules: `${CLAUDE_PLUGIN_ROOT}/reference/sloyd-api.md`.
Real-world sizes per piece: `${CLAUDE_PLUGIN_ROOT}/reference/tabletop-scale.md`.
Local tools: `PY="${CLAUDE_PLUGIN_DATA}/venv/bin/python"` (setup in mini-sculptor step 0).

## 1. Define the kit

Agree a kit card with the GM before generating anything:

```
Kit: Sunken Temple of Vael   Scale: 28mm   Style: HandpaintedStylized
Style anchor: "weathered green-veined marble, gold leaf worn to bronze, moss and roots, drowned temple"
Pieces (real size -> table footprint):
  - broken column x3       10 ft tall        1x1 square
  - ruined wall corner x2  8 ft x 10 ft      2x1 squares   -> modular (split)
  - altar                  4 ft tall         1x1
  - crates/urns scatter    2.5 ft            half square
  - dead tree              14 ft (shrunk)    1x1
```

Rules of thumb:
- 6-10 pieces cover an encounter.
- Mix 1 hero piece (statue, altar), 2-3 line-of-sight blockers (walls, columns, trees) and the rest small scatter.
- Footprints are 12.7 / 25.4 / 50.8 mm so pieces snap to a 1" grid.
- Leave 1 square of open floor around blockers so minis can still stand there.

## 2. Consistency strategy

1. Generate the **hero piece** concept first with `generate_image`, using the style anchor and
   `genStyleId`, with "isolated object, plain light grey background, three-quarter view, no ground, no shadow".
2. `upload_image` that concept (free) and pass its `jobId` as `referenceImageJobId` to every
   other piece's `generate_image`. That keeps materials and palette consistent.
3. Use the same style anchor sentence, `genStyleId` and `textureResolution` for every piece.

## 3. Make each piece

| Piece type | Tool | Credits |
|---|---|---|
| simple props (crate, barrel, urn, rock) | `generate_3d_from_text` with the style anchor; `textureResolution: "none"` if only printing | 25 (15) |
| hero/look-critical pieces | concept `generate_image` (+ reference) -> `generate_3d_from_image` | 30 |
| modular sets (walls, ruins, towers) | generate the assembled piece, then `split_model_into_parts` | +40 |

Prompt pieces as **chunky, solid, flat-bottomed**: "sits flat on the ground, thick walls,
broken edges are blocky, no thin spikes, no floating debris". Rubble that's attached to the base
is fine. Loose pebbles are not.

## 4. Modular pieces with `split_model_into_parts`

Use it for ruin walls, towers, bridges, or anything bigger than the printer bed:

```json
{"jobId": "<assembled model jobId>", "method": "partition", "numberOfParts": 6, "attachmentPoints": true}
```

- `partition` cuts along natural seams and caps each cut flat, so every part prints standing on
  its cut face. `attachmentPoints: true` adds pins and holes so parts register when glued, or
  dry-fit for swappable ruins. It takes about 4 minutes. The GLB must be 16 MB or smaller.
- Use `decomposition` only when you want reusable separate layers (for example a statue apart from
  its plinth). It has no textures and overlapping parts.

## 5. Scale and export (one scale for the whole kit)

```bash
# single piece: size by real height or by longest side
$PY "${CLAUDE_PLUGIN_ROOT}/scripts/mini_forge.py" terrain column.glb -o kit/column.stl --scale 28 --height-ft 10
$PY "${CLAUDE_PLUGIN_ROOT}/scripts/mini_forge.py" terrain crate.glb  -o kit/crate.stl  --scale 28 --footprint-ft 2.5
# split model: one STL per part, all at the same scale, in assembled position
$PY "${CLAUDE_PLUGIN_ROOT}/scripts/mini_forge.py" terrain wall_split.glb -o kit/wall/ --parts --scale 28 --footprint-ft 10
```

The script cuts 0.4 mm off the bottom to make it flat, centers the piece, and reports
`grid_squares` (footprint in 1" squares). If the footprint is far off the kit card, fix the size.
Then render the kit together:

```bash
$PY "${CLAUDE_PLUGIN_ROOT}/scripts/render_preview.py" kit/*.stl -o kit/kit_preview.png --size 1600x900
```

## 6. Print notes for terrain

- FDM, 0.4 nozzle, 0.16-0.2 mm layers, 2 walls, 10-15% infill, no supports. The flat bottoms are designed for that.
- Glue split parts with superglue. With pins, dry-fit first and sand the pin by 0.1 mm if it's tight.
- Paint fast: black primer, heavy drybrush in 2 tones, one wash. Terrain doesn't need mini-level detail.

Hand off: list pieces, sizes in mm, footprints in squares, STL paths. Offer **scene-painter** for a
matching battle map so printed terrain and the map share a palette.
