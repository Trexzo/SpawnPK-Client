# Chat 2 — inline image style subsystem R361

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/o` -> `CLIENT_CLASS_000504` -> `InlineImageStyleMarkup`
- `rs/l/o$a` -> `CLIENT_CLASS_000505` -> `InlineImageStyleSpec`
- `rs/l/n` -> `CLIENT_CLASS_000503` -> `SpriteStyleTransformer`
- review: `SEMREVIEW_49F01869CDD5BB11DD38`

## Shared img/timg style payload

The parser handles `img=` payloads and is reused by R360 `timg`.

It accepts up to five colon-delimited fields with exact bounds:

- image id <= 100000;
- style/color-transform value <= 511;
- size adjustment <= 99;
- two optional RGB colors <= 0xFFFFFF.

The parsed spec feeds Sprite transformation plus optional two-layer decoration around the
inline image.

## SpriteStyleTransformer

The transformer creates a resized Sprite using nearest-neighbor source sampling. The parsed
size adjustment expands width/height, with a hard 65,536-pixel output safety limit.

Non-zero style values apply color transformation through the shared `rs/l/L` color math;
values above 255 create a vertical phase/gradient variant.

A 128-entry four-way cache is keyed by source Sprite identity, style and size.

R55 `RSFont` uses this path for both ordinary inline images and R360 labeled `timg`
images.

`rs/l/L` remains unnamed as low-level reusable color math.

R361 remains non-canonical semantic research only.
