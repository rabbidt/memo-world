# Hand-made models

Drop `.glb` files here and list them in `manifest.json` to replace the built-in shapes:

```json
{ "models": [ { "name": "library_tower", "file": "library_tower.glb" } ] }
```

`name` is the kind of object it replaces (`notice_board`, `burrow`, `workshop_hut`, `library_tower`,
`pond`, `garden_plot`, `computer`, `lantern`, `bench`, `stump`, `signpost`, `tree`, `pine`, `rock`, `bush`),
or one of `memo_childlike`, `memo_young`, `memo_growing_up`, `memo_grown` for Memo himself.

Conventions: 1 unit = 1 metre, +Y up, origin at the centre of the ground, facing +Z.
For Memo, name the nodes `Body`, `Sprout`, `EyeL`, `EyeR`, `ArmL`, `ArmR`, `Notebook`, `Tail`, `FootL`,
`FootR` so the code can animate them. Anything not listed keeps its built-in shape.
