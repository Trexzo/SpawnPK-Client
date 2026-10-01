# Chat 2 — R412 duplicate classic-rendering audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R412 retains **no semantic proposal**.

A fresh exact-v308/historical-source comparison rediscovered three classic rendering roles,
but the global owner map proves all three were already recovered:

- `rs/l/F` -> `CLIENT_CLASS_000355` -> `Sprite` — already R55
- `rs/l/K` -> `CLIENT_CLASS_000360` -> `TextDrawingArea` — already R55
- `rs/l/C` -> `CLIENT_CLASS_000352` -> `DepthBufferedImageSurface` — already R85

R55 also already owns:

- `rs/l/E` -> `Rasterizer3D`
- `rs/l/c` -> `DrawingArea`

The attempted R412 name `RSImageProducer` for `rs/l/C` was therefore not only duplicate
ownership but also less precise than the retained R85 semantic name.

## Corroboration

The new audit still strengthens the older reviews:

- `rs/l/F` has the classic Sprite pixel/dimension/offset/cache-archive contract and matches
  historical 317-era Sprite source structure.
- `rs/l/K` loads a named font plus `index.dat`, owns glyph masks/metrics and Random-based
  text effects, matching historical TextDrawingArea structure.
- `rs/l/C` owns an int framebuffer, parallel float depth buffer and BufferedImage backed
  directly by the int buffer, corroborating R85 `DepthBufferedImageSurface`.

## Boundary

The attempted R412 candidate/review/test artifacts are removed. R412 is a
zero-retained duplicate/corroboration audit only.
