# Chat 2 — exact-v308 timed text effects R407

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/A` -> `CLIENT_CLASS_000350` -> `TypewriterTextEffectProcessor`
- `rs/l/l` -> `CLIENT_CLASS_000501` -> `FlashingTextEffectProcessor`
- review: `SEMREVIEW_367282BD91E25C9ED280`

## Typewriter effect

`rs/l/A` recognizes:

- `@type@`
- `<type>`
- `</type>`
- `<type=N>`

Opening tags are rewritten to timestamp-bearing state:

`<type=speed:timestamp>`

Default speed is **75 ms per character**. Explicit speed is clamped to **10..2000 ms**.
The render parser derives the visible-character count from elapsed time divided by speed.

Client owns exactly one instance and polls its active predicate so animated text can request
continued redraws. Both live font renderers (`rs/l/h`, `rs/l/k`) consume the static
type-tag helpers.

## Flashing effect

`rs/l/l` recognizes:

- `@fla@`
- `@fla2@`
- `<fla>`
- `<fla2>`
- matching closing tags
- explicit-color `<fla=N>` / `<fla2=N>`

The processor injects timestamps into the active tags.

The render-state function alternates the requested color with the hidden/sentinel state on a
**200 ms** cadence.

- `fla` window: **600 ms**
- `fla2` window: **1200 ms**

Client owns one instance and includes its active predicate in the same redraw decision as the
typewriter processor.

## Boundary

These are descriptive behavior names. No verbatim original source identifiers are claimed.
R407 remains non-canonical semantic research only.
