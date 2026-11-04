#!/usr/bin/env bash
# Launch demo: 4 party minis + owlbear + modular ruin wall + battle map + skybox, end to end.
# Needs SLOYD_CLIENT_ID / SLOYD_CLIENT_SECRET and ~410 credits. Re-runnable: finished jobs are skipped.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
S="$ROOT/scripts"
OUT="${OUT:-$HERE/out}"
VENV="${VENV:-$HERE/.venv}"

[ -x "$VENV/bin/python" ] || { python3 -m venv "$VENV" && "$VENV/bin/pip" install -q -r "$ROOT/requirements.txt"; }
PY="$VENV/bin/python"

# 1. Sloyd jobs (balance check, cost, max 5 concurrent, downloads + manifest.json)
[ "${SKIP_JOBS:-0}" = 1 ] || python3 "$S/sloyd_api.py" plan "$HERE/plan.json" --out "$OUT/jobs" --yes

J="$OUT/jobs"
mkdir -p "$OUT/stl" "$OUT/media" "$OUT/tokens"

# 2. Party minis: true relative scale, 25 mm bases with magnet recess
declare -A RACE=([brakka]=dwarf [sel]=tiefling [pip]=halfling [kaelen]=elf)
declare -A RING=([brakka]="#f15bb5" [sel]="#45bcff" [pip]="#03f584" [kaelen]="#06f5d4")
for k in brakka sel pip kaelen; do
  "$PY" "$S/mini_forge.py" mini "$J/${k}_3d.glb" -o "$OUT/stl/${k}_28mm.stl" \
    --scale 28 --race "${RACE[$k]}" --size medium --magnet 6x2 --json > "$OUT/stl/${k}_report.json"
  "$PY" "$S/scene_tools.py" sheet "$J/${k}_concept.png" "$J/${k}_left.png" "$J/${k}_back.png" \
    -o "$OUT/media/${k}_turnaround.png" --labels "Front|Left|Back"
  "$PY" "$S/scene_tools.py" token "$J/${k}_concept.png" -o "$OUT/tokens/${k}.png" --ring "${RING[$k]}"
  "$PY" "$S/render_preview.py" "$OUT/stl/${k}_28mm.stl" -o "$OUT/media/${k}_preview.png"
done

# 3. Owlbear: Large, 50 mm hollow base, rearing (~9 ft)
"$PY" "$S/mini_forge.py" mini "$J/owlbear_3d.glb" -o "$OUT/stl/owlbear_28mm.stl" \
  --scale 28 --size large --height-ft 9 --json > "$OUT/stl/owlbear_report.json"

# 4. Terrain: ruined wall, whole + split parts, same scale (10 ft long)
"$PY" "$S/mini_forge.py" terrain "$J/wall_3d.glb" -o "$OUT/stl/ruin_wall.stl" --scale 28 --footprint-ft 10 --json > "$OUT/stl/ruin_wall_report.json"
"$PY" "$S/mini_forge.py" terrain "$J/wall_split.glb" -o "$OUT/stl/ruin_wall_parts" --parts --scale 28 --footprint-ft 10 --json > "$OUT/stl/ruin_wall_parts_report.json"

# 5. Battle map + skybox, table-ready
"$PY" "$S/scene_tools.py" grid  "$J/map.png" -o "$OUT/media/map_foundry_24x14.png" --cols 24 --rows 14 --px 100
"$PY" "$S/scene_tools.py" print "$J/map.png" -o "$OUT/media/map_print_letter.pdf" --cols 24 --rows 14
PANO="$(ls "$J"/skybox_panoramaUrl.* 2>/dev/null | head -1 || true)"
[ -n "$PANO" ] && "$PY" "$S/scene_tools.py" still "$PANO" -o "$OUT/media/tavern_tv.png" --fov 95

# 6. Hero shots
"$PY" "$S/render_preview.py" "$OUT"/stl/{pip,brakka,kaelen,sel}_28mm.stl "$OUT/stl/owlbear_28mm.stl" \
  -o "$OUT/media/lineup.png" --size 1600x900 --title "The Ember Road Company + owlbear, 28mm"
"$PY" "$S/render_preview.py" "$OUT/stl/brakka_28mm.stl" -o "$OUT/media/brakka_turntable.gif" --turntable 36 --size 720x900
"$PY" "$S/scene_tools.py" sheet "$J"/{brakka,sel,pip,kaelen}_concept.png -o "$OUT/media/party_concepts.png" \
  --labels "Brakka|Sel|Pip|Kaelen"

echo "done -> $OUT"
