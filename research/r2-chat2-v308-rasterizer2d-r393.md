# Chat 2 — Rasterizer2D R393

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/M` -> `CLIENT_CLASS_000362` -> `Rasterizer2D`
- proposal: `SEMPROP_CA3A017457BA709681FF`
- review: `SEMREVIEW_6B800A55183782E32B16`

## Exact surface

The class owns its own software-raster state:

- pixel buffer;
- width / height;
- clipping bounds;
- row/offset arrays.

Its static primitive surface includes:

- clip reset/set;
- horizontal/vertical lines;
- rectangle borders/fills;
- alpha variants;
- arbitrary integer line rasterization.

The general line method contains the expected Bresenham-style major-axis stepping.

## Consumer

R55 `RSFont` calls the class directly for text strike/line rendering.

The class extends R55 `DrawingArea`, but its independent raster state and broad primitive
API prove that it is not merely a tiny font helper.

## Naming boundary

The descriptive/historical role is `Rasterizer2D`. The existing `DrawingArea` semantic
identity remains distinct; R393 does not rename or supersede it.

R393 is non-canonical semantic research only.
