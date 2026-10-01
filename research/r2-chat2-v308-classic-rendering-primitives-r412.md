# Chat 2 — classic rendering primitives R412

Exact client authority: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/C` -> `CLIENT_CLASS_000352` -> `RSImageProducer`
- `rs/l/F` -> `CLIENT_CLASS_000355` -> `Sprite`
- `rs/l/K` -> `CLIENT_CLASS_000360` -> `TextDrawingArea`
- review: `SEMREVIEW_D1314D25BA3E22361A20`

These names are supported first by exact-v308 behavior and only then corroborated by
historical RS-client source.

### RSImageProducer

Owns the software framebuffer int[] plus parallel float depth buffer and a BufferedImage
directly backed by that pixel array. It binds those buffers into the shared raster state and
presents the image through AWT Graphics.

### Sprite

Owns the central sprite pixel array, dimensions, offsets and canvas/max dimensions; supports
cache/image constructors plus direct, alpha, masked, scaled and transformed drawing. It has
very high exact-v308 fan-out across the UI/rendering system.

### TextDrawingArea

Loads named font data plus index.dat through the cache archive, maintains per-glyph masks and
metrics, and implements the classic text measurement/drawing/effect surface. The constructor
and field layout directly match historic TextDrawingArea implementations.

R412 remains non-canonical semantic research only.
