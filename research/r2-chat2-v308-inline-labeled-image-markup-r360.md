# Chat 2 — inline labeled-image markup R360

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/y` -> `CLIENT_CLASS_000518` -> `InlineLabeledImageMarkup`
- `rs/l/y$a` -> `CLIENT_CLASS_000519` -> `InlineLabeledImageSpec`
- review: `SEMREVIEW_4FF376C1639DAAA1461C`

## Exact markup

The parser recognizes:

`<timg=...>label</timg>`

The opening payload is parsed through the shared inline-image style parser. The parser then
captures all text through the exact `</timg>` closing tag and caches the result.

## RSFont rendering

R55 `RSFont`:

1. resolves the parsed image id into the inline Sprite table;
2. applies the shared image resize/recolor/style transform;
3. positions and draws the Sprite inline;
4. when inner text is present, temporarily resets font formatting and renders that label
   centered inside the image;
5. restores the previous font state and advances beyond the complete markup span.

The parsed spec stores only the image/style/label/end-index state consumed by that path.

R360 remains non-canonical semantic research only.
