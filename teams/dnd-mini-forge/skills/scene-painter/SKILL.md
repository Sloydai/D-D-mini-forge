---
name: scene-painter
description: Create 360-degree skybox backdrops for virtual tabletops and session ambience (Tabletop Simulator, TV/second screen, VTT scene backgrounds) with Sloyd generate_skybox / edit_skybox, and top-down gridded battle maps with generate_image, sized for Foundry, Roll20 or Owlbear and printable on a 1-inch grid. Use for battle maps, encounter maps, VTT backgrounds, skyboxes, and setting the mood for a session.
---

# Scene Painter

You paint the world around the minis: the **battle map** they stand on and the **skybox** the
players look into. Everything you deliver has to work on the table: exact pixels per square
for VTTs, true 1-inch squares on paper, and backdrops cropped for a TV.

Sloyd API rules: `${CLAUDE_PLUGIN_ROOT}/reference/sloyd-api.md`.
Local tools: `PY="${CLAUDE_PLUGIN_DATA}/venv/bin/python"` (setup in mini-sculptor step 0).

## 1. Battle map (`generate_image`, 10 credits)

Agree the encounter: location, size in squares (typical 20x15 to 30x20; 1 square = 5 ft),
features that matter mechanically (cover, difficult terrain, chokepoints, an elevation change, an
exit), light level, and how it will be used (VTT, print, or both).

Pick `aspectRatio` closest to cols:rows (`16:9` for 32x18 or 24x14, `3:2` for 30x20, `4:3` for
20x15, `1:1` for 20x20) and prompt:

```
Top-down orthographic battle map for a tabletop RPG, viewed straight down, no perspective.
{location}: {layout described in squares: "a 10-foot-wide stone bridge crosses a chasm north to south,
two broken pillars give half cover on the east side, a collapsed archway blocks the far end"}.
{lighting / mood}. Clear readable floor, features sized for 5-foot squares (a door is one square wide).
No grid lines, no characters, no tokens, no text, no UI, no frame.
```

`genStyleId`: `HandpaintedStylized` reads best on a VTT. Use `Realistic` for gritty campaigns.
Download `outputs.imageUrl`. For a night or flooded variant of the same map, run `edit_image` on its
`jobId` ("same map at night, lit by braziers", 15 credits).

Make it table-ready:

```bash
# VTT: exact px per square (Foundry default 100, Roll20 70). VTTs draw their own grid.
$PY "${CLAUDE_PLUGIN_ROOT}/scripts/scene_tools.py" grid map.png -o map_foundry.png --cols 24 --rows 14 --px 100
# Print for in-person play: 1-inch squares across Letter/A4 pages, print at 100%
$PY "${CLAUDE_PLUGIN_ROOT}/scripts/scene_tools.py" print map.png -o map_print.pdf --cols 24 --rows 14 --paper letter
```

Tell the user the VTT setting: Foundry Grid Size = px, Roll20 page = cols x rows units.

## 2. Skybox backdrop (`generate_skybox`, 25 credits)

A skybox is a 360 equirectangular panorama (`outputs.panoramaUrl`) plus six cubemap faces
(`outputs.cubemapFaceUrls`). Uses at the table:

- **Tabletop Simulator:** Options -> Backgrounds -> Custom, paste the panorama URL. The table now sits inside the scene.
- **Session ambience:** a still view on a TV or second screen behind the GM screen. Crop it:
  `scene_tools.py still pano.png -o tv.png --yaw 0 --fov 90 --size 1920x1080`
- **VTT scene backgrounds / theatre of the mind:** use the same still crop as the scene image.
- **3D VTTs and game engines:** the cubemap faces.

Prompt from eye level, as the place the party stands in:

```
360-degree panorama from eye level inside {place}: {what's around, near and far}, {time of day},
{weather}, {light sources}. {mood}. Rich detail at the horizon, readable sky.
```

**Mood shifts with `edit_skybox`** (25 credits each) on the skybox `jobId` keep the same place:
"same tavern, now on fire, smoke along the ceiling" or "same forest at dusk, fog rolling in". Prepare
2-3 before a session and switch when the dragon arrives.

`generate_skybox_from_image` can turn a battle map or concept art into a matching 360. `upload_image`
the art first (free), then pass `imageJobId`.

## 3. Tokens for online play

For party minis, make matching round VTT tokens from the concept front views:

```bash
$PY "${CLAUDE_PLUGIN_ROOT}/scripts/scene_tools.py" token mini-forge/<slug>/concept.png -o tokens/<slug>.png --ring "#03f584"
```

Give each player a different ring color so tokens are easy to tell apart.

## 4. Hand-off

Deliver: `map.png` (raw), `map_<vtt>.png`, `map_print.pdf`, `skybox_pano.png`, `tv.png`, any mood
variants, and the exact VTT settings. Costs: map 10, map variant 15, skybox 25, mood edit 25.
