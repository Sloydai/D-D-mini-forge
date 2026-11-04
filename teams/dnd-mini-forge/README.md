# D&D Mini Forge

**Describe your character. Print your mini.**

Claude skills for tabletop players and GMs, powered by the [Sloyd API](https://www.sloyd.ai/api).
Paste a character (or your whole party) and get concept art, a front/side/back turnaround, a 3D
model, and a **print-ready STL at true 28mm or 32mm heroic scale on a 25 mm round base**. GMs also
get bestiary minis on the right base for their size category, a matching scatter-terrain kit,
gridded battle maps for Foundry, Roll20 or paper, and 360 skyboxes for session ambience.

## The team

| Skill | Role | Sloyd tools | Ends in |
|---|---|---|---|
| `party-forge` | Producer. "Make minis for my whole party." Parses the roster, budgets, schedules every job within the 5-job limit | all of the below, `get_credit_balance` | party folder: STLs, line-up render, VTT tokens |
| `character-designer` | Concept artist. Rewrites the design so it survives printing, then concept + turnaround | `generate_image`, `edit_image` | `concept.png`, `left.png`, `back.png`, `character.json` |
| `mini-sculptor` | Sculptor and print tech. 3D from the turnaround, then the local scale/base/STL step | `generate_3d_from_images`, `generate_3d_from_image` | `<name>_28mm.stl`, preview, resin/FDM settings |
| `monster-workshop` | Bestiary. Size category -> base, bipeds by height, beasts by footprint, flyers on stands | `generate_image`, `generate_3d_from_image(s)`, `split_model_into_parts`, `retexture_model` | encounter STLs on 25-100 mm bases |
| `terrain-builder` | Terrain crafter. One style anchor, grid-sized footprints, modular pieces with pins | `generate_3d_from_text`, `generate_image`, `upload_image`, `split_model_into_parts` | flat-bottomed terrain STLs, one per part |
| `scene-painter` | Map and mood. Top-down battle maps and 360 skyboxes, mood swaps mid-session | `generate_image`, `edit_image`, `generate_skybox`, `edit_skybox`, `generate_skybox_from_image` | VTT PNG at exact px/square, printable 1" grid PDF, TV backdrop |

How the skills hand off:

```
party description -> party-forge
  -> character-designer (concept -> left + back views)
  -> mini-sculptor (multi-view 3D -> mini_forge.py: scale, base, STL)
  -> monster-workshop / terrain-builder / scene-painter for the GM's side of the table
```

## Folder tree

```
teams/dnd-mini-forge/
├── .claude-plugin/plugin.json      # plugin "dnd-mini-forge" v0.1.0
├── .mcp.json                       # connects the hosted Sloyd MCP with your env keys
├── README.md
├── TWEET.md                        # launch tweet, alt hooks, demo shot list
├── requirements.txt                # trimesh, manifold3d, numpy, pillow, ...
├── reference/
│   ├── sloyd-api.md                # tools, job loop, credits, errors, REST fallback
│   ├── tabletop-scale.md           # 28 vs 32mm, size->base, terrain sizes, min feature sizes
│   └── printing-guide.md           # resin vs FDM settings, orientation, magnets
├── scripts/
│   ├── mini_forge.py               # GLB -> scaled mini on a round base -> STL (+ terrain, sizes)
│   ├── render_preview.py           # grey-resin PNG / turntable GIF / line-up renders
│   ├── scene_tools.py              # battle-map grid + print PDF, skybox stills, tokens, sheets
│   └── sloyd_api.py                # stdlib Sloyd client + plan runner (MCP or REST)
├── skills/
│   ├── party-forge/SKILL.md
│   ├── character-designer/SKILL.md
│   ├── mini-sculptor/SKILL.md
│   ├── monster-workshop/SKILL.md
│   ├── terrain-builder/SKILL.md
│   └── scene-painter/SKILL.md
└── examples/demo-party/            # the launch demo: party.md, plan.json, run_demo.sh
```

## Install

1. Get Sloyd API keys at [api-dashboard.sloyd.ai](https://api-dashboard.sloyd.ai) (API Keys ->
   Generate Key) and add prepaid credits. The minimum is $12 for 900 credits, enough for about 12 party minis.
2. Export the keys in the shell you start Claude Code from. Don't commit them.

   ```bash
   export SLOYD_CLIENT_ID=sok_live_...
   export SLOYD_CLIENT_SECRET=...
   ```

3. Install the plugin. It connects the Sloyd MCP server for you through `.mcp.json`:

   ```bash
   claude plugin marketplace add Sloydai/D-D-mini-forge
   claude plugin install dnd-mini-forge@sloyd-dnd-mini-forge
   ```

   Or in one step inside Claude Code (v2.1.275+): `/plugin install dnd-mini-forge --marketplace Sloydai/D-D-mini-forge`

   To connect the Sloyd MCP yourself instead, for example to use it outside this plugin:

   ```bash
   claude mcp add --transport http sloyd https://api.sloyd.ai/api/mcp \
     --header "x-client-id: $SLOYD_CLIENT_ID" --header "x-client-secret: $SLOYD_CLIENT_SECRET"
   ```

4. The local print tools need Python 3.10+. The skills set up a venv on first use
   (`pip install -r requirements.txt`). Nothing else is required: no Blender, no GPU.

## Examples

> **"Make minis for my whole party:** Brakka, hill dwarf forge cleric with a big warhammer and tower
> shield; Sel, tiefling warlock with hellfire in her hand; Pip, halfling rogue with two daggers;
> Kaelen, wood elf ranger with a longbow. 28mm, for my resin printer."

party-forge shows the roster and the cost (4 x 70 = 280 credits, about $3.73). It then runs 4
concepts, 8 views and 4 multi-view 3D jobs, never more than 5 at a time. The result is four STLs at
true relative height: the halfling 15 mm, the dwarf 22 mm, the elf 28 mm, the tiefling 30 mm, each on
a 25 mm base with a 6x2 magnet recess. You also get a line-up render, VTT tokens, and resin settings.

> "I need an owlbear for next session, and it's rearing up."

monster-workshop sizes it Large on a 50 mm hollow base and scales it by height (9 ft = 46 mm),
for 30 credits.

> "Dungeon dressing for a sunken temple: columns, a ruined wall I can rearrange, some urns."

terrain-builder defines a kit card with one style anchor, then splits the wall into 6 pinned parts
with `split_model_into_parts`. Every piece comes out at one scale with a flat bottom and a footprint
in grid squares.

> "Battle map for the owlbear's ruined courtyard, 24x14 squares, for Foundry and to print."

scene-painter makes a top-down map at 2400x1400 (Foundry Grid Size 100) and a 6-page Letter PDF
with 1-inch squares (10 credits). Add a forge-tavern skybox for session zero, plus an "it's on
fire now" variant (`edit_skybox`).

The local tools also work on their own, on any GLB/OBJ/STL:

```bash
python scripts/mini_forge.py mini hero.glb -o hero_28mm.stl --race dwarf --magnet 6x2
python scripts/mini_forge.py mini dragon.glb -o dragon.stl --size huge --fit footprint --flight-stand 35
python scripts/mini_forge.py terrain ruin_split.glb -o ruin/ --parts --footprint-ft 10
python scripts/mini_forge.py sizes        # size categories, bases, race heights at 28/32mm
python scripts/render_preview.py hero_28mm.stl -o hero.gif --turntable 36
python scripts/scene_tools.py print map.png -o map.pdf --cols 24 --rows 14 --paper a4
```

## Costs (Sloyd API credits, 75 credits = $1)

| What | Credits |
|---|---|
| party mini (concept 10 + 2 views 30 + multi-view 3D 30) | 70 (~$0.93) |
| monster from one image (concept 10 + 3D 20) | 30 |
| simple terrain prop (text-to-3D, textured / geometry only) | 25 / 15 |
| modular split | 40 |
| battle map / variant | 10 / 15 |
| skybox / mood edit | 25 / 25 |

Every skill checks your balance and states the cost before it spends anything. A failed job is refunded.
Pricing: [sloyd.ai/api/pricing](https://www.sloyd.ai/api/pricing).

## Scale notes

1 inch of grid = 5 ft. 28mm heroic is ~1:60 (a 6 ft human is 30 mm), 32mm heroic is ~1:54 (34 mm).
Tiny, Small and Medium creatures go on 25 mm bases, Large 50, Huge 75, Gargantuan 100. Details are in
[`reference/tabletop-scale.md`](reference/tabletop-scale.md).

Privacy: generation runs on Sloyd. See the [Sloyd privacy policy](https://www.sloyd.ai/privacy-policy).
