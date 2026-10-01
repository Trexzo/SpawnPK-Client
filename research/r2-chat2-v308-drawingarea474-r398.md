# Chat 2 — DrawingArea474 R398

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/M` -> `CLIENT_CLASS_000362` -> `DrawingArea474`
- proposal: `SEMPROP_865C3CAD77128C9BEB3F`
- review: `SEMREVIEW_5515DA35764F8D61BED0`

## Exact rendering role

R55 already fixes:

- `rs/l/c` -> `DrawingArea`
- `rs/l/h` -> `RSFont`

Direct `rs/l/M` extends DrawingArea and owns a separate static 2D raster surface with:

- pixel array;
- clip bounds;
- row/offset arrays;
- raster reset/setup helpers;
- horizontal and vertical line primitives;
- outlined/filled rectangle helpers;
- alpha variants;
- arbitrary-line drawing;
- gradient-like primitive paths.

## Live RSFont join

RSFont calls `rs/l/M.h(int,int,int,int)` from its live rich-text draw path for horizontal
rules used by underline/strikethrough presentation.

This establishes `rs/l/M` as the auxiliary primitive drawing layer used by the newer
RSFont engine rather than dead duplicate raster code.

## Historical lineage

474-era RSPS client source commonly retains a separate class named `DrawingArea474`
beside classic `DrawingArea` and `RSFont`. That class supplies the newer-font/UI drawing
primitives, matching exact v308's structure and consumer pattern.

Historical naming is corroboration only; exact-v308 bytecode is primary authority.

R398 remains non-canonical semantic research only.
