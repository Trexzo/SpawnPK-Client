# Chat 2 — R484 duplicate Overlay value audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R484 retains **no semantic proposal**.

The exact-v308 literal/source scan independently recovered:

- `rs/l/f/c` -> `OverlayBounds`
- `rs/l/f/f` -> `OverlayMenuEntry`

However, R12 already owns both exact classes with the same proposal identities:

- `OverlayBounds`: `SEMPROP_01ABB62F3DEE55929BF2`
- `OverlayMenuEntry`: `SEMPROP_A555897388EBF2921283`

The stronger later source fingerprinting is retained only as corroboration. The R484
candidate/review/test artifacts are removed to preserve repository-wide semantic uniqueness.

R484 is a correction/audit batch only.
