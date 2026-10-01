# Chat 2 — exact-v308 Jagex printable character matcher R469

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Corrected result

R469 retains exactly one genuinely new semantic proposal:

- `rs/A/k` -> `CLIENT_CLASS_000014` -> `JagexPrintableCharMatcher`
- proposal: `SEMPROP_3AB6BDA5EEA000DFBA1B`
- review: `SEMREVIEW_0EC372F479267AA6F843`

The original R469 batch also attempted:

- `rs/A/d` -> `AsyncBufferedImage`

That tuple was already owned by R20 with the exact same proposal ID
`SEMPROP_0A95AE215FCE838836DC`, so it has been removed from R469.

## JagexPrintableCharMatcher

Exact v308 extends Guava `CharMatcher` and accepts:

- ASCII printable characters 32..126;
- codepoint 128;
- codepoints 160..255.

The contract matches historical RuneLite `JagexPrintableCharMatcher`.

## Boundary

R469 is non-canonical semantic research only.
