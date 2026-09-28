# Chat 2 — timed text effects R356

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/A` -> `CLIENT_CLASS_000350` -> `TypewriterTextEffect`
- `rs/l/l` -> `CLIENT_CLASS_000501` -> `FlashingTextEffect`
- review: `SEMREVIEW_9A97D3BC816564588632`

## TypewriterTextEffect

Exact markup:

- `@type@`
- `<type>`
- `<type=N>`
- `</type>`

Parameterized speed is clamped to 10..2000 ms. The class rewrites the markup with a
timestamp, computes visible-character progress from elapsed time / interval, and exposes
active-state lifecycle so the font renderer can keep redrawing until the reveal completes.

## FlashingTextEffect

Exact markup:

- `@fla@`
- `@fla2@`
- `<fla>`
- `<fla2>`
- `<fla=...>`
- `<fla2=...>`
- closing tags for fla/fla2

The primary flash toggles on 200 ms intervals over a 600 ms lifecycle. The secondary fla2
path uses a 1200 ms lifecycle and also derives a decaying sinusoidal displacement.

Both are invoked directly from the R55 RSFont rendering pipeline.

R356 remains non-canonical semantic research only.
