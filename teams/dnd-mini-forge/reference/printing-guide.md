# Printing minis and terrain: resin vs FDM

## Which printer for what

| Thing | Best | Why |
|---|---|---|
| player characters, monsters up to Large | resin (MSLA) | 0.03-0.05 mm layers keep faces, hands and buckles |
| Huge/Gargantuan monsters | resin hollowed, or FDM 0.2 nozzle | volume and cost |
| scatter terrain (crates, pillars, walls) | FDM | sturdy, cheap, flat bottoms need no supports |
| trees, organic ruins | either; FDM with organic/tree supports | |
| multicolor without painting | FDM with AMS/MMU, model made with `genStyleId: "Color3DPrint"` | flat color regions print as separate filaments |

## Resin (Elegoo, Anycubic, Phrozen, Saturn/Mars class)

- **Orientation:** tilt the mini 30-45 deg backwards so the face and front never carry supports.
  Don't print the base flat on the plate, it causes suction cups and elephant foot. Either tilt the
  whole mini, or print base-down on a raft only if your slicer adds suction relief holes.
- **Supports:** auto "medium" plus light supports on chin, nose tip, fingers and weapon tips
  (lowest points of each "island"). Check the slicer's island detection after rotating.
- **Hollowing:** don't hollow minis under ~40 mm, they're nearly solid anyway. Hollow Large+ at
  1.5-2 mm walls and add two drain holes under the base. `mini_forge.py` already makes bases of 50 mm
  and up hollow underneath.
- **Layer height:** 0.03-0.05 mm. Exposure: use your resin's validation matrix result.
- **After:** wash in IPA or water-washable bath 2-3 min, dry fully, cure 2-4 min (over-curing makes swords brittle).
- **Magnets:** the `--magnet 6x2` recess is 6.2 x 2.1 mm. Superglue in a 6x2 mm neodymium magnet;
  steel washers or a magnetic sheet in the carry case keep minis from rattling.

## FDM (Bambu, Prusa, Creality class)

- **Nozzle:** 0.2 mm for character minis (huge improvement in faces); 0.4 mm is fine for terrain
  and for 32mm-scale or larger monsters.
- **Layers:** 0.08-0.12 mm for minis, 0.16-0.2 mm for terrain.
- **Supports:** organic/tree supports (Orca, Bambu Studio, PrusaSlicer, Cura). Touch-point 0.3-0.4 mm.
- **Speed and cooling:** outer walls 30-50 mm/s. Print 3-4 minis on a plate so each layer has time to
  cool. 2 walls, 15% infill.
- **Orientation:** upright on the base. The flat base is the first layer, no brim needed with PEI plates.
- **Terrain:** print without supports. `mini_forge.py terrain` cuts a flat bottom; split pieces have
  pins and holes when `attachmentPoints` was on.

## Checklist before slicing

1. `mini_forge.py` reported no "feet overhang" or "under 18 mm" warnings, or you accepted them.
2. The preview render looks right: the base is centered under the feet and the figure doesn't lean.
3. The slicer's repair ran clean. AI meshes can have small holes; "merged-shells" output is expected and fine.
4. For resin: islands supported, mini tilted, drain holes on hollow bases.
