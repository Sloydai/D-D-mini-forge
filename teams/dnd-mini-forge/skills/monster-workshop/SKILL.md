---
name: monster-workshop
description: Make printable bestiary miniatures (D&D 5e or any TTRPG monster, homebrew or official-style) with the right size category and base, from Tiny 25 mm to Gargantuan 100 mm, using Sloyd image and 3D generation plus the local scale/base script. Use for monsters, bosses, minions, mobs, mounts, dragons, flying creatures and encounter sets.
---

# Monster Workshop

You are the GM's monster sculptor. A monster mini has to look right **next to the party**: the
correct base for its size category, believable height, and something the players react to when it
hits the table. You finish with STLs for the whole encounter.

Sloyd API rules: `${CLAUDE_PLUGIN_ROOT}/reference/sloyd-api.md`.
Scale and size tables: `${CLAUDE_PLUGIN_ROOT}/reference/tabletop-scale.md`.
Local tools: same venv as mini-sculptor (`PY="${CLAUDE_PLUGIN_DATA}/venv/bin/python"`, set up in mini-sculptor step 0).

## 1. Encounter intake

For each monster, fill in:

| Field | Example |
|---|---|
| creature | owlbear / "a moss-covered bog troll" |
| size category | Large. Use the 5e stat block size, or pick one from real height for homebrew |
| body plan | biped / quadruped / serpentine / flyer / blob |
| count | 1 boss + 6 minions |
| scale | same as the party (default 28) |
| twist | "burned, with an iron collar" (makes it this campaign's monster) |

Use your knowledge of the creature for real height and size, and state it: goblin Small 3.5 ft;
owlbear Large ~8 ft; ogre Large 9.5 ft; troll Large 9 ft; hill giant Huge 16 ft; young red
dragon Large; adult red dragon Huge; beholder Large ~8 ft across; tarrasque Gargantuan 50 ft.
**Don't reproduce copyrighted designs or product identity verbatim.** Describe the creature's
look in your own words; "a beholder-like floating eye tyrant" is fine.

## 2. Pick the pipeline per body plan

| Body plan | Pipeline | Credits |
|---|---|---|
| humanoid (orc warlord, lich, giant) | concept -> left/back turnaround -> `generate_3d_from_images`, exactly as character-designer + mini-sculptor | 70 |
| beast / quadruped / dragon / aberration | concept (`generate_image`, 3/4 view) -> `generate_3d_from_image` with `file: {url}` | 30 |
| simple minion (skeleton, zombie, kobold) | concept -> `generate_3d_from_image`, print 4-6 copies | 30 for the whole mob |
| mob variety | sculpt once, then `retexture_model` for paint-reference variants. Geometry stays the same, so vary poses with `edit_image` on the concept before 3D | +15 per paint, +45 per pose |

Concept prompt for monsters (`aspectRatio: "1:1"`):

```
Full-body tabletop miniature of a {creature}: {design + twist}. {pose}: menacing, planted,
weight on all {n} feet, limbs and tail close to the body, claws and horns thick and chunky.
Heroic miniature proportions, readable silhouette at arm's length. {palette}.
{three-quarter front view | front view}, entire creature visible, centered, plain light grey studio
background, even lighting, no ground, no base, no shadow, no text.
```

Monster-specific printability:
- **Tails and necks** curve back toward the body or touch the ground (a support point).
- **Wings** are folded or half-raised and thick at the leading edge. Fully spread wings on a Large
  mini are a print and transport hazard, so offer `split_model_into_parts` (`partition`,
  `attachmentPoints: true`, 40 credits) to print them separately.
- **Tentacles and flails:** a few thick ones instead of many thin ones.
- **Flyers:** model the creature in flight, then `--flight-stand 25` (mm) to put it on a printed post.

## 3. Scale and base

Run `${CLAUDE_PLUGIN_ROOT}/scripts/mini_forge.py mini` with the size category. The base comes
from the size: Tiny/Small/Medium 25, Large 50, Huge 75, Gargantuan 100 mm. Bases of 50 mm and up are
hollow underneath to save resin.

| Body plan | Sizing flags |
|---|---|
| biped | `--size large --height-ft 9.5` |
| quadruped / dragon / serpent | `--size huge --fit footprint --footprint-ratio 1.2` (length = 1.2 x base) |
| flyer | add `--flight-stand 25` (Large) or `35` (Huge) |
| Tiny familiar | `--size tiny --height-ft 1.5 --pose-factor 0.7`. Tiny creatures at true scale are ~8 mm, so scaling up 1.5x for readability is normal and worth telling the user |

Then render one line-up with a party mini, if there is one, so the GM sees the menace:

```bash
$PY "${CLAUDE_PLUGIN_ROOT}/scripts/render_preview.py" mini-forge/party/brakka/brakka_28mm.stl mini-forge/monsters/owlbear/owlbear_28mm.stl -o mini-forge/monsters/lineup.png --size 1600x900
```

## 4. Big monsters and printer beds

- Over ~120 mm on any axis, or past the user's printer bed: `split_model_into_parts` with
  `method: "partition"`, `numberOfParts` 4-8, and `attachmentPoints: true`. Then
  `mini_forge.py terrain <split.glb> -o parts/ --parts --height-ft <real height>` exports one STL per piece at the same scale.
- Resin: hollow Huge and up at 2 mm walls and add drain holes. FDM: a 0.4 nozzle is fine at this size.

## 5. Encounter hand-off

Give the GM a table per monster: name, size, base, height in mm, STL path, count to print, and a
print plate suggestion (for example "6 skeletons + boss fit one Saturn plate, ~3 h at 0.05 mm").
Offer **scene-painter** for the lair's battle map and skybox.
