# Chat 2 — glow and progress-bar rich text R410

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/m` -> `CLIENT_CLASS_000502` -> `RichTextGlowEffectProcessor`
- `rs/l/v` -> `CLIENT_CLASS_000513` -> `RichTextProgressBarProcessor`
- `rs/l/v$a` -> `CLIENT_CLASS_000514` -> `RichTextProgressBarSpec`
- review: `SEMREVIEW_D3B47F1B3F32B4D052F6`

## Glow effect

The glow processor recognizes `glo` plus numbered `glo2..glo9` markup and explicit
color forms.

Its global phase is:

`(nanoTime / 1_000_000 / 40) & 255`

and per-glyph lookup additionally offsets phase by glyph position before selecting one of
nine 256-entry palettes. Those palettes are generated from rainbow, grayscale and multi-stop
RGB interpolation functions.

The live font renderer consumes the parsed glow style and phase for every glyph.

## Progress bars

`rs/l/v` parses `pbar` markup and caches parsed results in a 256-slot identity/range cache.

Exact behavior includes:

- width clamp: **20..300 px**;
- parsed current/max fraction clamped to **0..1**;
- configurable frame/background/fill colors;
- optional embedded label text;
- styles 1..7;
- static fill and animated gradient variants.

Animated styles advance from `nanoTime / 8 ms`, use 512- or 1536-step cycles, and request
continued redraw through the R409 motion/redraw helper.

`rs/l/v$a` is the immutable parsed bar spec consumed directly by the renderer.

R410 remains non-canonical semantic research only.
