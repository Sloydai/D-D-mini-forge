# Tabletop scale cheat sheet

## Scale

- Battle grid: 1 inch (25.4 mm) square = 5 ft. That is about 1:60.
- **28mm heroic** (D&D standard, WizKids, Reaper, most STL Patreons): 1:60, 5.08 mm per ft.
  A 6 ft human is ~30 mm to the top of the head, ~28 mm to the eyes.
- **32mm heroic** (modern Games Workshop, many indie sculptors): 1:54, 5.64 mm per ft.
  A 6 ft human is ~34 mm.
- Don't mix the two scales at one table without warning the group. A 32mm fighter towers over 28mm goblins.
- "Heroic" means the proportions are exaggerated so the mini reads at arm's length: heads about 1/6 of
  body height, hands and weapons about 1.2-1.5x real size, thicker limbs and blades.

## Size category to base

| Size | Space | Base | Examples | Sizing rule for `mini_forge.py` |
|---|---|---|---|---|
| Tiny | 2.5 ft | 25 mm (20 mm optional) | imp, pseudodragon, cat, sprite | `--height-ft` real height, often looks lost; scale up to 1.5x for readability |
| Small | 5 ft | 25 mm | halfling, gnome, goblin, kobold | `--race` or `--height-ft` |
| Medium | 5 ft | 25 mm (32 mm for 32mm-scale) | human, orc, ghoul, mind flayer | `--race` or `--height-ft` |
| Large | 10 ft | 50 mm | ogre, owlbear, horse, troll, young dragon | bipeds by height (ogre 9.5 ft), quadrupeds `--fit footprint` |
| Huge | 15 ft | 75 mm | hill giant (16 ft), treant, adult dragon | giants by height, dragons footprint 1.0-1.3 |
| Gargantuan | 20 ft+ | 100 mm (or bigger) | ancient dragon, kraken, purple worm, tarrasque | `--fit footprint`, often split for the printer bed |

Bases fit inside their grid squares (25 mm in a 25.4 mm square, 50 in 50.8, 75 in 76.2, 100 in 101.6).

## Real-world sizes for terrain (feet, at 28mm in mm)

| Piece | Real size | 28mm print |
|---|---|---|
| crate | 2.5 ft cube | 12.7 mm |
| barrel | 3 ft tall | 15 mm |
| table | 2.5 ft tall, 5 ft long | 13 x 25 mm |
| door | 7 ft tall, 4 ft wide | 36 x 20 mm |
| dungeon pillar | 10-12 ft | 50-60 mm |
| ruined wall section | 8 ft tall, 10 ft long | 40 x 50 mm |
| statue on plinth | 9 ft | 46 mm |
| tree | 20-30 ft real, use 12-16 ft (60-80 mm) so minis can stand near it | 60-80 mm |
| standing stone | 8 ft | 40 mm |
| campfire ring | 4 ft across | 20 mm |

Table-scale trees and buildings are usually compressed ("scale-shrunk") so they don't dominate the map.
Footprints should be whole or half squares (12.7, 25.4, 50.8 mm) so pieces sit cleanly on the grid.

## Printability rules at 28mm (1 mm on the mini = 2.4 inches in-world)

| Detail | Resin minimum | FDM 0.4 nozzle | FDM 0.2 nozzle |
|---|---|---|---|
| freestanding wire (spear shaft, staff) | 0.8 mm, better 1.2 | 1.6 mm | 1.0 mm |
| sword blade thickness | 0.6 mm | 1.2 mm | 0.8 mm |
| raised detail (belt, buckle) | 0.15 mm | 0.4 mm | 0.25 mm |
| gap that stays open | 0.4 mm | 0.8 mm | 0.5 mm |

So in the design: bowstrings, chains, whips, rapier tips, fingers spread wide and floating spell effects
do not survive. Close them up, thicken them, or attach them to the body.
