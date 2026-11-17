# Blender asset pipeline

Seed-driven generators, run with Blender 5.1 headless. Everything is original geometry and textures made by
these scripts.

**State on 2026-11-17: work is paused, waiting for a texture pack from Rob.** The models currently in
`web/assets/models/` are still the first pass. The generators here are the newer hero-quality pass and
have not been exported into the repo yet (the last full build was interrupted before its shared textures
were written correctly).

```bash
blender -b --factory-startup --python build.py -- all ../../web/assets/models
```

`what` can be `all` or any of `ash,trees,walls,world,extra` (comma separated).

- `memo_lib.py`: primitives; `Part` (merged solid pieces, baked AO in vertex colour) and `RawPart` (textured
  geometry with hand-set normals, UVs and colours); the generated textures (leaf atlas, bark, stone); export.
  Textured models are written as `.gltf` + `.bin` and share one copy of each texture in `_tex/`.
- `memo_trees.py`: trees, pines and shrubs. Trunk curve, forking branches, leaf-clump scatter, colour
  gradient, textured bark, one canopy node per season, and a `_lod1` of each.
- `memo_walls.py`: dry-stone walls along any path. The rules are listed at the top of the file.
- `memo_world.py`, `memo_extra.py`: buildings, props, and the bridge, beach hut, waterfall, campfire and
  observatory.
- `memo_ash.py`: Ash the wolf as a blockout measured from Rob's character sheet. `ash_shots.py` and
  `ash_compare.py` overlay its orthographic renders on the sheet (the sheet itself is not in this repo).
- `hero.py`: golden-hour close-up, mid shot and turntable of one model. `compose.py`: the whole island.
  `preview.py`: a line-up of any models.
- `wolf_build.py`, `memo_char.py`: earlier approaches, kept for reference and no longer used.

Conventions: 1 unit = 1 metre, +Y up, origin at ground centre, front facing +Z. `manifest.json` lists every
model with its size, triangle count, node pivots and `optional_nodes`.

Optional nodes are exported at scale 0.001 so they stay invisible until the game scales them to 1:
`Canopy_spring`, `Canopy_autumn`, `Canopy_winter` (summer is the visible default), `Leaves_*` on shrubs,
and `Snow` on roofed buildings.

Character nodes: `Body` (with `EyeL`, `EyeR`, `ArmL`, `ArmR`, `Tail` as children and `Notebook` under
`ArmR`), `FootL`, `FootR`.
