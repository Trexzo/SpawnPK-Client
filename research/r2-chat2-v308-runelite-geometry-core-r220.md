# Chat 2 — exact-v308 RuneLite geometry/core API source recovery R220

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R220 is a separate non-canonical class-only review for ten exact-v308 classes whose stripped names can be recovered from historical RuneLite source provenance.

## Deterministic review result

- candidate classes: **10**
- resolved proposals: **10**
- unresolved: **0**
- review ID: `SEMREVIEW_EA7F7B04B71D7BC455B6`
- field/method proposals: **0**

## Stable IDs

- `rs/runelite/a/b` -> `CLIENT_CLASS_000810` -> `Constants`
- `rs/runelite/a/e` -> `CLIENT_CLASS_000813` -> `Jarvis`
- `rs/runelite/a/f` -> `CLIENT_CLASS_000814` -> `LocalPoint`
- `rs/runelite/a/h` -> `CLIENT_CLASS_000816` -> `Perspective`
- `rs/runelite/a/i` -> `CLIENT_CLASS_000817` -> `Point`
- `rs/runelite/a/l` -> `CLIENT_CLASS_000825` -> `Shapes`
- `rs/runelite/a/l$a` -> `CLIENT_CLASS_000826` -> `ShapeIterator`
- `rs/runelite/a/m` -> `CLIENT_CLASS_000827` -> `SimplePolygon`
- `rs/runelite/a/m$a` -> `CLIENT_CLASS_000828` -> `SimpleIterator`
- `rs/runelite/a/m$b` -> `CLIENT_CLASS_000829` -> `TransformIterator`

## Upstream source authority

Historical RuneLite commit `b0a10a9c14686f4012eb30865261bbeb3d55af4b` contains the corresponding source types in `runelite-api`:

- `net.runelite.api.Constants`;
- `net.runelite.api.Point`;
- `net.runelite.api.Perspective`;
- `net.runelite.api.coords.LocalPoint`;
- `net.runelite.api.geometry.Shapes` and its private `ShapeIterator`;
- `net.runelite.api.geometry.SimplePolygon` and its private `SimpleIterator` / `TransformIterator`;
- `net.runelite.api.model.Jarvis`.

This is source-name provenance, not merely naming by adjacency. The pinned v308 bytecode keeps the distinctive constant sets, method families, data shapes and geometry algorithms of those upstream classes. SpawnPK has local adaptations in some client access paths, so confidence remains **0.999**, not 1.0.

## Exact-v308 evidence

### Constants

The exact class retains the fixed-client dimensions and aspect ratio, zoom, chunk/region/scene dimensions, plane/tile flag values, tick lengths, item-sprite dimensions and high-alchemy multiplier from RuneLite `Constants`.

### Jarvis

The exact class retains both convex-hull entry points and the Jarvis-march helpers (`square`, left-most search and cross product), producing the same SimplePolygon representation.

### LocalPoint / Point / Perspective

`LocalPoint` retains the two-int local-coordinate value type and scene/world conversion behavior. `Point` retains the two-int canvas point value object and Euclidean distance. `Perspective` retains the projection, tile-polygon, text/image/sprite placement, model projection and clickbox families joining those value types to Client and Model geometry.

### Shapes / SimplePolygon

`Shapes` is the generic Shape aggregator with the exact nested path iterator. `SimplePolygon` retains the x/y arrays, left/right indexing, 16-element growth, append/reverse, Sutherland-Hodgman clipping, Shape implementation and both nested iterators.

## Synthetic boundary

R220 deliberately does not name adjacent empty/switch-map helpers such as `rs/runelite/a/k` or `rs/runelite/a/n`. No source-level semantic class is invented for compiler artifacts.

## Acceptance boundary

Chat 2 does not promote R220. Main/Core may accept any subset only through an explicit `semantic_acceptance_spec` bound to `SEMREVIEW_EA7F7B04B71D7BC455B6`.
