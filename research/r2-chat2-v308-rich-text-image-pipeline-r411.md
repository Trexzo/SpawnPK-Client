# Chat 2 — embedded rich-text image pipeline R411

Exact client authority: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/n` -> `CLIENT_CLASS_000503` -> `RichTextSpriteTransformCache`
- `rs/l/o` -> `CLIENT_CLASS_000504` -> `RichTextImageSpecParser`
- `rs/l/o$a` -> `CLIENT_CLASS_000505` -> `RichTextImageSpec`
- `rs/l/y` -> `CLIENT_CLASS_000518` -> `RichTextLabeledImageProcessor`
- `rs/l/y$a` -> `CLIENT_CLASS_000519` -> `RichTextLabeledImageSpec`
- review: `SEMREVIEW_8DBA546263B1CE46DEEC`

The generic `<img=...>` parser accepts sprite id plus transform/size/frame parameters,
validates them, and caches parsed specs. The font renderer selects the sprite, sends it
through the 128-entry transform cache, optionally draws the two-layer frame, and renders it
inline.

`<timg=...>label</timg>` reuses the same image spec but additionally captures the enclosed
label. The renderer draws that label centered over the transformed image.

The names are descriptive exact-v308 behavior names only. R411 remains non-canonical.
