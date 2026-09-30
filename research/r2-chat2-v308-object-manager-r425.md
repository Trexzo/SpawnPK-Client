# Chat 2 — exact-v308 ObjectManager R425

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/x` -> `CLIENT_CLASS_001114` -> `ObjectManager`
- proposal: `SEMPROP_3CB4FC4EF6994A842D12`
- review: `SEMREVIEW_E80B92D2470E8CC80E1D`

## Exact-v308 role

`rs/x` is the terrain/landscape scene manager.

Its constructor receives:

- `byte[][][]` tile/plane flags;
- `int[][][]` terrain heights.

It initializes the characteristic classic-client region state:

- minimum/active plane sentinel = 99;
- region dimensions = 104 x 104;
- four-plane 104x104 tile work arrays;
- 105x105 lighting/shading working state.

Its scene-build pass accepts the collision-map array plus the scene/world-controller object
and walks the four 104x104 planes to:

- apply collision blocking;
- derive tile lighting;
- accumulate floor underlay/overlay colour state;
- construct scene tiles;
- apply occlusion/plane information.

The class also owns terrain-region/chunk decode and landscape-object placement paths.

## R424 join

R424 `TerrainHeightNoise` has exactly one live external class consumer: `rs/x`.

The plane-0 terrain decode path stores:

`-8 * TerrainHeightNoise(worldX + 932731, worldY + 556238)`

Higher planes derive height from the preceding plane instead.

## Historical source identity

Classic 317 source trees preserve the exact class name `ObjectManager` with the same:

- `ObjectManager(byte[][][], int[][][])` constructor shape;
- initial 99/104/104 region state;
- collision-map + world-controller scene-build architecture;
- terrain/object region responsibilities.

That exact structural continuity is stronger than a merely descriptive modern name.

## Boundary

R425 is non-canonical semantic research only. Chat 2 does not perform acceptance or source rewrite.
