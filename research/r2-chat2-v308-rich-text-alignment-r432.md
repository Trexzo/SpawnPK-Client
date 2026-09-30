# Chat 2 — exact-v308 rich-text alignment state R432

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/x` -> `CLIENT_CLASS_000516` -> `RichTextAlignmentState`
- `rs/l/x$a` -> `CLIENT_CLASS_000517` -> `RichTextAlignment`
- review: `SEMREVIEW_D27D4B151B3A1212872D`

## Exact enum identity

The nested enum preserves the literal constants:

- `LEFT`
- `CENTER`
- `RIGHT`

No inferred enum names are needed.

## Exact parser/state behavior

`rs/l/x` owns one singleton instance containing:

- the alignment enum;
- one auxiliary integer.

Its static String parser resets the singleton, scans angle-bracket markup and recognizes:

- `align`
- `hov=...`

The align route sets alignment state to `LEFT`.

The hov route parses numeric text through the existing client numeric helpers and stores the
resulting integer. Exact v308 does not expose a surviving external consumer that proves what
the hov integer means, so R432 intentionally leaves that field semantically opaque.

## Liveness boundary

A whole-JAR direct class-reference scan finds no external exact-v308 owner of `rs/l/x`.
The pair survives as isolated/dormant utility code.

That does not prevent descriptive recovery because the parser grammar and enum constants are
self-identifying, but R432 makes no claim that the feature is exercised by the live v308 UI.

R432 remains non-canonical semantic research only.
