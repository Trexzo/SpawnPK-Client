# Chat 2 — classic rendering source identities R421

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/C` -> `CLIENT_CLASS_000352` -> `RSImageProducer`
- `rs/l/E` -> `CLIENT_CLASS_000354` -> `Rasterizer`
- `rs/l/F` -> `CLIENT_CLASS_000355` -> `Sprite`
- `rs/l/K` -> `CLIENT_CLASS_000360` -> `TextDrawingArea`
- review: `SEMREVIEW_362C9AD13A50BFF671DB`

These names are backed first by exact-v308 structure/live use and then corroborated by
historical 317 source fingerprints.

`rs/l/M` was inspected in the same pass. It contains a complete secondary clipped 2D
raster implementation but has no exact-v308 reverse references, so it remains intentionally
unnamed rather than being promoted from dead compatibility code.

R421 remains non-canonical semantic research only.
