# Chat 2 — exact-v308 typewriter text effect R428

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/A` -> `CLIENT_CLASS_000350` -> `TypewriterTextEffect`
- proposal: `SEMPROP_5DB53882E872168FACE3`
- review: `SEMREVIEW_F661854FA178ACDB3DB0`

## Markup surface

The class recognizes four typing markers:

- `@type@`
- `<type>`
- `<type=N>`
- `</type>`

Default delay is **75 ms** per visible character.

Explicit `N` is clamped to **10..2000 ms**.

## Timestamp rewrite

The preprocessing path converts a typing marker to:

`<type=delay:startMillis>`

where `startMillis` is derived from `System.nanoTime()/1_000_000`.

When invoked in the stateful path, it also computes and stores the expected completion
deadline from the largest active delay and the count of visible characters after stripping
markup.

## RSFont reveal behavior

R55 RSFont delegates type-tag parsing to this class during glyph traversal.

For a timestamped type tag, the parser computes the currently revealable character count as
approximately:

`floor((now - startMillis) / delayMillis) + 1`

and returns a dedicated close-tag sentinel for `</type>`.

Malformed type metadata is rejected rather than guessed.

## Client lifecycle

Client owns exactly one instance.

Client:

- preprocesses display strings through the effect;
- combines it with the other recovered rich-text effect pipeline;
- checks its completion/redraw latch during the live frame path.

The class therefore owns the timed character-reveal effect itself, not generic rich-text
parsing.

## Boundary

`TypewriterTextEffect` is descriptive exact-v308 terminology. No verbatim original source
identifier is claimed.

R428 remains non-canonical Chat 2 research only.
