# Chat 2 — exact-v308 SceneOverlay recovery R240

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- raw class: `rs/s/c/f`
- stable ID: `CLIENT_CLASS_000893`
- source identity: `SceneOverlay`
- confidence: **0.999**
- review: `SEMREVIEW_99941BBFB32C82849AA4`
- unresolved: **0**
- field/method proposals: **0**

## Exact v308 evidence

`rs/s/c/f` extends the recovered Overlay base and carries a highly distinctive scene-debug constant set:

- map-square color: green
- chunk-border color: blue
- local-valid-movement color: `(141, 220, 26)`
- valid-movement color: `(73, 122, 18)`
- line-of-sight color: `(204, 42, 219)`
- interacting color: cyan
- local tile size: `128`
- chunk size: `8`
- map-square size: `64`
- chunk-border cull: `16`
- stroke width: `4`
- interacting shift: `-16`

Its render path consumes local/world scene coordinates, constructs map-square/grid paths, labels scene/map-square positions, and renders Developer Tools scene diagnostics.

## Historical source provenance

RuneLite `SceneOverlay` at `68c819924cfd6bfb4848c71f74c121109f289d5a` has the same overlay role and distinctive color/geometry signature. SpawnPK has extended the tooling, including its mouse/selection behavior, but the surviving constant and rendering fingerprint fixes the source identity.

## Acceptance boundary

R240 remains non-canonical. Chat 2 performs no semantic acceptance.
