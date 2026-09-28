# Chat 2 — exact-v308 animated sprite sequence R309

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/l/a/b` -> `CLIENT_CLASS_000365` -> `AnimatedSpriteSequence`
- review: `SEMREVIEW_355A96AA9839EF9BF032`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

The class is a reusable timed sequence of `Sprite` frames:

- one constructor accepts a caller-supplied `Sprite[]` plus frame interval;
- the other accepts a base resource name, frame count and interval and loads `baseName + index` for every frame;
- the current-frame index advances only after the millisecond deadline and wraps cyclically to zero;
- `c()` returns the current frame after performing the timing update;
- three public drawing wrappers delegate to three separate `Sprite` draw methods using that current frame.

Exact v308 initializes the shared singleton with:

- base name `glitter`;
- **4** frames;
- **100 ms** frame interval.

The semantic noun is therefore kept generic as `AnimatedSpriteSequence`; `Glitter*` would describe only one instance, not the class contract.

## Boundary

R309 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
