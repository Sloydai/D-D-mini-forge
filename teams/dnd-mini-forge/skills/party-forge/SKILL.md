---
name: party-forge
description: Orchestrate the D&D Mini Forge team to make printable miniatures for a whole adventuring party from one pasted party description (or a list of character sheets). Runs character-designer and mini-sculptor for every member in parallel within Sloyd's 5-job limit, keeps scale and style consistent, and ends with a folder of STLs, a line-up render and VTT tokens. Use for "make minis for my whole party", session zero, or gifting minis to players.
---

# Party Forge

You are the producer. Your players paste their characters in, and they walk away with STLs that
match each other: one scale, one base standard, one art style. Lean on the specialists and follow
their skills exactly:

- **character-designer** (`skills/character-designer`): concept + turnaround
- **mini-sculptor** (`skills/mini-sculptor`): 3D, scale, base, STL, print advice
- **monster-workshop** for animal companions, familiars and mounts
- **scene-painter** for tokens and an optional session-zero backdrop

Sloyd API rules: `${CLAUDE_PLUGIN_ROOT}/reference/sloyd-api.md`.

## 1. Parse the party

Turn the paste into a roster table and show it. Infer missing fields, mark guesses with `?`, and
keep each player's own words for the vibe.

| # | Name | Race | Class (lvl) | Hero item | Pose | Palette | Size/base |
|---|---|---|---|---|---|---|---|
| 1 | Brakka | hill dwarf | Forge Cleric 5 | warhammer on shoulder | defiant stance | soot, brass, ember | Medium / 25 |

Party-wide settings (confirm once):
- **Scale:** 28mm default. Never mix scales in one party.
- **Base:** 25 mm round for Small and Medium. Add a magnet recess if they use a carry case.
- **Style:** one `genStyleId` for everyone. `HandpaintedStylized` by default, `Color3DPrint` for multicolor FDM.
- **Companions:** a ranger's wolf or a wizard's owl go to monster-workshop. Note them as extra rows.
- **Review:** "review" stops after concepts for player approval (recommended for gifts). "fast" runs straight through.

## 2. Budget, then go

Per character: concept 10 + left 15 + back 15 + 3D 30 = **70 credits**.
Companion (concept + single-image 3D): 30.

Call `get_credit_balance` and present the plan: "4 heroes + 1 wolf = 310 credits (about $4.13).
Balance 900. Go?" On 402 at any point, stop, keep the finished results, and say exactly how
many credits are missing.

## 3. Schedule within the 5-job limit

Dependencies per character: `concept -> (left, back) -> 3D -> local STL`.

Use a rolling queue and never more than 5 active jobs:
1. Start all concepts (up to 5).
2. As each concept finishes (review mode: once the player approves it), start its two edits.
3. As both views of a character finish, start its 3D job.
4. Every time a job finishes, fill the free slot with the next ready job. Prefer jobs that unblock
   3D (views) over new concepts, so finished minis arrive early.
5. On 429, don't retry in a loop. Poll the running jobs with `get_job` `wait: 30` and start the next job
   when one finishes.
6. Run the local STL step (`mini_forge.py mini`) as soon as each GLB lands. It's free and instant.

Without MCP tools, write the same graph as a plan file and run it. The runner handles the
5-job limit, 429, 402 and downloads:

```json
[
  {"id": "brakka_concept", "tool": "generate_image", "args": {"prompt": "...", "aspectRatio": "1:1", "genStyleId": "HandpaintedStylized"}},
  {"id": "brakka_left", "tool": "edit_image", "args": {"jobId": "{{brakka_concept.jobId}}", "prompt": "..."}},
  {"id": "brakka_back", "tool": "edit_image", "args": {"jobId": "{{brakka_concept.jobId}}", "prompt": "..."}},
  {"id": "brakka_3d", "tool": "generate_3d_from_images", "args": {
    "frontImage": {"url": "{{brakka_concept.imageUrl}}"}, "leftImage": {"url": "{{brakka_left.imageUrl}}"},
    "backImage": {"url": "{{brakka_back.imageUrl}}"}, "EnablePBR": "true", "FaceCount": "300000"}}
]
```

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sloyd_api.py" plan mini-forge/party/plan.json --out mini-forge/party/jobs --yes
```

The runner writes `manifest.json` and can be re-run. Finished steps are skipped, so a run cut off
by 402 resumes after a top-up.

## 4. Consistency checks across the party

Before 3D, put the concepts side by side:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scene_tools.py" sheet a/concept.png b/concept.png c/concept.png d/concept.png -o mini-forge/party/concepts.png --labels "Brakka|Sel|Pip|Vex"
```

- Do they share one style and similar lighting and level of detail?
- Does each one have a distinct silhouette, so players tell their minis apart on the table?
- Are the relative sizes believable? The script scales by race height, so the halfling ends up waist-high to the goliath automatically.

## 5. Deliver

```
mini-forge/party/
  concepts.png            # roster art
  lineup.png              # all STLs rendered together at true relative scale
  <slug>/concept.png left.png back.png <slug>.glb <slug>_28mm.stl preview.png
  tokens/<slug>.png       # VTT tokens, one ring color per player
```

```bash
$PY "${CLAUDE_PLUGIN_ROOT}/scripts/render_preview.py" mini-forge/party/*/*_28mm.stl -o mini-forge/party/lineup.png --size 1600x900 --title "The party, 28mm"
```

Close with:
- a table of name, height in mm, base, STL path, and resin ml or filament g;
- one print plate suggestion: a 4-person party fits one resin plate, ~2-3 h at 0.05 mm, tilted 35 deg;
- the total credits spent.

Offer scene-painter for a session-zero tavern skybox and monster-workshop for their first boss.
