# Launch tweet: D&D Mini Forge

> **Rule for this launch: every image and clip shows real output from this team.** Use the files
> that `examples/demo-party/run_demo.sh` writes to `examples/demo-party/out/media/` from a real
> Sloyd run. No mockups, no stock minis. The only AI-video shots are the opening and closing clips,
> and they animate a render of the actual generated mini.

## Main tweet (thread 1/3)

```
My players describe their character.
10 minutes later it's printing.

D&D Mini Forge: Claude skills that turn a character sheet into a 28mm mini, on its base, ready to slice.

Free on GitHub, powered by @SloydAi 👇
```

Media: the 30-40 s demo video (shot list below). Fallback image: `media/lineup.png`.

## 2/3: what's inside

```
6 skills, one team:

party-forge         paste your party → all the minis
character-designer  concept + front/side/back
mini-sculptor       3D → true 28/32mm, 25mm base, STL
monster-workshop    Tiny→Gargantuan on the right base
terrain-builder     modular scatter terrain
scene-painter       battle maps + 360 skyboxes
```

Media: `media/brakka_turnaround.png` → `media/brakka_turntable.gif` (2 images), or `media/party_concepts.png`.

## 3/3: install + link

```
Install in Claude Code:

claude plugin marketplace add Sloydai/D-D-mini-forge
claude plugin install dnd-mini-forge@sloyd-dnd-mini-forge

~$0.93 per mini. Bring your own printer.
github.com/Sloydai/D-D-mini-forge
```

Media: `media/map_foundry_24x14.png` (the owlbear's battle map), showing it does maps too.

## Alt hooks

1. `My DM made my character into a real mini before session 1 even started. It took one paragraph.`
2. `Your party in Discord: 4 paragraphs of backstory. Your party on the table: 4 minis on 25mm bases. Same evening.`

Spare for the GM audience: `GMs: paste your encounter, get the owlbear on a 50mm base, the ruins, and the battle map.`

## Demo video shot list (9:16 and 4:5, 30-40 s, Poppins captions, Sloyd navy/green)

| # | Time | Shot | Source (real output) | Caption |
|---|---|---|---|---|
| 1 | 0-3 s | **Open on the real world:** photoreal clip of the printed, painted Brakka mini on a game table among dice and a character sheet, slow push-in | AI image-to-video (Sloyd video, `frames` mode) from a photoreal still made from `brakka_preview.png` + `brakka_concept.png`. Save its first frame for shot 9. | "My players describe their character…" |
| 2 | 3-6 s | Discord-style message with the party paste from `party.md`, pasted into Claude Code | screen recording | — |
| 3 | 6-9 s | Claude Code shows the roster table and "280 credits, about $3.73. Go?" → "yes" | screen recording of the real run | "…it checks the cost first" |
| 4 | 9-14 s | Four concept images pop in one after another, then Brakka's front/left/back sheet | `party_concepts.png`, `brakka_turnaround.png` | "concept → turnaround" |
| 5 | 14-19 s | Brakka's turntable, grey resin on the 25 mm base | `brakka_turntable.gif` | "true 28mm, 25mm base, magnet slot" |
| 6 | 19-23 s | Line-up: halfling to tiefling at true relative height, plus the owlbear on 50 mm | `lineup.png` (slow pan) | "the whole party. and the owlbear." |
| 7 | 23-27 s | STL dropped into a slicer (Chitubox, Lychee or Bambu), tilt 35°, supports, "Print" | screen recording with `brakka_28mm.stl` | "…10 minutes later it's printing" |
| 8 | 27-31 s | Quick cuts: battle map with the Foundry grid, tavern skybox still, VTT tokens | `map_foundry_24x14.png`, `tavern_tv.png`, `tokens/*.png` | "maps, terrain, skyboxes too" |
| 9 | 31-35 s | **Close on the real world:** the same table, the mini now joined by the rest of the printed party; the last frame matches shot 1's first frame for a seamless loop | AI image-to-video in start/end-frame mode, end frame = shot 1 first frame | "D&D Mini Forge · free on GitHub" + logo |

Production notes:
- Shots 3 and 7 must be real screen recordings of the real run, not re-creations.
- In shot 3, keep the credit numbers visible. They're real and the price is a selling point.
- Caption style: two-part headline with one accent word in brand green `#03f584`; CTA pill uses the
  cyan→green gradient `linear-gradient(63deg,#45bcff 19%,#03f584 100%)` with `#021225` text.
- Post 9:16 on X, Shorts and Reels, and 4:5 for the in-feed version.

## Status of the real assets

| Asset | Status |
|---|---|
| `examples/demo-party/plan.json` (22 Sloyd jobs, 410 credits) | ready |
| `run_demo.sh` pipeline (scale/base/STL, renders, map, skybox, tokens) | tested end to end with stand-in models |
| real Sloyd run → `out/media/*` | **pending: the API key has 0 credits.** Top up ~410 credits, then run `examples/demo-party/run_demo.sh` |
