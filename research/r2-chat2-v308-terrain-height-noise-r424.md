# Chat 2 — exact-v308 terrain height noise R424

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/p` -> `CLIENT_CLASS_000739` -> `TerrainHeightNoise`
- proposal: `SEMPROP_00D9935988755F54F41F`
- review: `SEMREVIEW_50850EAD03B9D0DAA49B`

## Exact behavior

`rs/p` is a stateless static numeric helper. Its live external consumer is the terrain
decode path in `rs/x`.

For plane 0, that path stores tile height as:

`-8 * rs/p.a(worldX + 932731, worldY + 556238)`

For higher planes the decoder instead derives the tile from the preceding plane by subtracting
240, separating `rs/p` specifically as the base-plane terrain-height source.

The public two-coordinate helper combines three exact noise scales:

- scale 4;
- scale 2 with half weighting;
- scale 1 with quarter weighting.

The combined value is transformed through `35 + 0.3 * value` and clamped to `10..60`.

Supporting methods implement deterministic coordinate hashing, neighbor-smoothed noise,
cosine-interpolated sampling and 2048-entry trigonometric lookup initialization.

## Boundary

The proposal deliberately names only the numeric terrain-height noise role. `rs/p` owns no
scene-object placement, tile storage, archive decoding or rendering state.

`TerrainHeightNoise` is a descriptive exact-v308 recovery; no verbatim stripped developer
identifier is claimed.

R424 remains non-canonical Chat 2 semantic research only. No acceptance or source rewrite is
performed.
