# Chat 2 — exact-v308 Bounds R365

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/g/a` -> `CLIENT_CLASS_000177` -> `Bounds`
- proposal: `SEMPROP_7E023E2EA223D9262EA7`
- review: `SEMREVIEW_4E74912844D1F6296FC4`

## Exact source fingerprint

The class has exactly four public integer fields corresponding to:

- lowX
- lowY
- highX
- highY

Its four-argument constructor sets the low pair and high pair through two mutators.

Its two-argument constructor delegates to:

`this(0, 0, arg1, arg2)`

Public RuneScape/RSPS source for `Bounds` matches this exact structure, including the
otherwise distinctive `toString() { return null; }` implementation.

This is therefore a recovered original framework identity, not merely a descriptive name.

R365 remains non-canonical semantic research only.
