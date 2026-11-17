# Hand-made models

Drop `.glb` files here and list them in `manifest.json` to replace the built-in shapes:

```json
{ "models": [ { "name": "library_tower", "file": "library_tower.glb" } ] }
```

`name` is the kind of object it replaces (`notice_board`, `burrow`, `workshop_hut`, `library_tower`,
`pond`, `garden_plot`, `computer`, `lantern`, `bench`, `stump`, `signpost`, `tree`, `pine`, `rock`, `bush`),
or one of `memo_pup`, `memo_young`, `memo_growing_up`, `memo_grown` for Ash the wolf himself.

Conventions: 1 unit = 1 metre, +Y up, origin at the centre of the ground, facing +Z.
For Ash, name the nodes `Body`, `EyeL`, `EyeR`, `ArmL`, `ArmR`, `Notebook`, `Tail`, `FootL`, `FootR`
so the code can animate them. `Sprout` is optional: give that name to the ears if you want them to twitch.
The same names with an `ash_` prefix work too, and `memo_childlike` is also accepted for the pup. Anything not listed keeps its built-in shape.
