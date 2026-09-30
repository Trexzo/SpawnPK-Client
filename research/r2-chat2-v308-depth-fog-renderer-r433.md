# Chat 2 — exact-v308 depth fog renderer R433

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/d` -> `CLIENT_CLASS_000390` -> `DepthFogRenderer`
- proposal: `SEMPROP_37B0AFF7868A1F955BE2`
- review: `SEMREVIEW_721FC99BC5282B4AD359`

## Exact raster contract

R55 already fixes `rs/l/c` as `DrawingArea` and records that it owns:

- the shared `int[]` pixel framebuffer;
- the shared `float[]` depth buffer;
- active width/height and clipping state.

`rs/l/d` consumes those same global buffers.

For each active pixel it compares depth against a near and far threshold:

- depth >= far -> replace pixel with the configured fog RGB;
- near <= depth < far -> blend current pixel toward fog RGB using an 8-bit factor;
- depth < near -> preserve the existing pixel.

The class also owns one float offset added to the supplied thresholds and one static fog color.

## Liveness boundary

A direct exact-v308 class-reference audit finds no surviving external caller for `rs/l/d`.
The renderer therefore appears dormant in this build.

The semantic behavior is nonetheless exact and self-contained, so R433 names the raster role
without claiming the live Client currently enables it.

R433 remains non-canonical semantic research only.
