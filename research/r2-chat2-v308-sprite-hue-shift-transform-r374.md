# Chat 2 — exact-v308 Sprite hue-shift color transform R374

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/L` -> `CLIENT_CLASS_000361` -> `SpriteHueShiftColorTransform`
- proposal: `SEMPROP_7C7FD25D897ED8583E64`
- review: `SEMREVIEW_392BB83D0E7FE3166E21`

R361 already fixes `rs/l/n` as `SpriteStyleTransformer`.

`rs/l/L` has no external exact-v308 owner other than that transformer.

Its main RGB transform:

1. extracts RGB channels;
2. computes max/min and chroma;
3. derives a six-sector hue;
4. applies a normalized hue offset;
5. wraps the hue modulo 1536;
6. reconstructs RGB;
7. blends original vs transformed channels with a clamped 0..100 percentage.

The Sprite transformer uses this result only on non-transparent Sprite pixels while
preserving alpha.

## Withheld neighbor

`rs/l/M` remains unnamed. R55 proves its base `rs/l/c` is `DrawingArea`, and
`rs/l/M` provides a large independent set of raster primitives consumed by R55
`RSFont`, but exact v308 does not preserve a sufficiently specific historical noun yet.

R374 remains non-canonical semantic research only.
