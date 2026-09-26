# Chat 2 — exact-v308 GroundMarkerOverlay recovery R241

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

- `rs/s/f/c` -> `CLIENT_CLASS_000909` -> `GroundMarkerOverlay`
- confidence: **0.999**
- review: `SEMREVIEW_95BC6E624B359474EB6B`
- unresolved: **0**
- field/method proposals: **0**

## Exact match

The v308 class extends Overlay and has the same Ground Markers render path as RuneLite source: plugin point collection, plane filter, per-marker color with config fallback, configurable border stroke, distance cutoff **32**, LocalPoint/tile-polygon conversion, fill opacity, and optional text label rendering.

Historical authority: RuneLite `GroundMarkerOverlay` at `68c819924cfd6bfb4848c71f74c121109f289d5a`.

The neighboring `rs/s/f/e` is a compiler-generated generic type-token helper and is deliberately left unnamed.

## Acceptance boundary

R241 remains non-canonical. Chat 2 performs no semantic acceptance.
