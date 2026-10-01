# Chat 2 — depth fog renderer R395

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/j` -> `CLIENT_CLASS_000300` -> `DepthFogRenderer`
- proposal: `SEMPROP_DECCA8C0AC1E423BCE5A`
- review: `SEMREVIEW_06419D231F26FB1BFFBD`

The stable ID is independently present in the recovered-source workspace as
`rs/j/Recovered_CLIENT_CLASS_000300.java`; it is not inferred from neighboring class order.

## Exact algorithm

The render pass walks the full DrawingArea surface, reading:

- the software float depth buffer;
- the destination RGB pixel buffer.

For each pixel:

- depth beyond the configured far threshold becomes the fog color;
- depth inside the transition range blends the current pixel toward the fog color;
- depth before the fog start is preserved.

The blend uses the standard masked red/blue + green channel arithmetic.

## State

The class owns:

- the current fog color;
- one float range/offset value.

It exposes setters for those values and no unrelated game-domain state.

## Corroboration

Public RSPS client lineage contains the same depth-buffer algorithm under `renderFog`
rasterizer code, independently supporting the fog role.

R395 remains non-canonical semantic research only.
