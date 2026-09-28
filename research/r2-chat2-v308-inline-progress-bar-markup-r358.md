# Chat 2 — inline progress-bar markup R358

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/v` -> `CLIENT_CLASS_000513` -> `InlineProgressBarMarkup`
- `rs/l/v$a` -> `CLIENT_CLASS_000514` -> `InlineProgressBarSpec`
- review: `SEMREVIEW_1992D79C7AD0CA5E72CF`

## Parser / renderer

The exact RSFont path recognizes inline `pbar` markup with numbered variants 2..7.
It parses colon-delimited numeric/style fields, clamps the requested width to **20..300**
pixels, supports an optional embedded label and caches parsed results.

Rendering is performed directly through R55 `DrawingArea`: background/border plus filled
progress region. Animated styles derive changing colors from a nanoTime phase and mark the
text pipeline for redraw.

## Parsed specification

`rs/l/v$a` is the immutable nine-field value passed from the parser to RSFont and the
renderer. It carries only the parsed bar/layout/style/label state and has no independent
behavior.

R358 remains non-canonical semantic research only.
