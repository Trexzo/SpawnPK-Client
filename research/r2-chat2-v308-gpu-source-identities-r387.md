# Chat 2 — R387 duplicate GPU color-blind enum audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R387 retains **no semantic proposal**.

The attempted R387 recovery:

- `rs/s/e/a`
- `CLIENT_CLASS_000900`
- `ColorBlindMode`

duplicates the already-authoritative R15 semantic name:

- `rs/k/a/b`
- `CLIENT_CLASS_000316`
- proposal: `SEMPROP_B861CE1199E8491D47B7`
- review: `SEMREVIEW_9F64F82DCFBF8C7A97EF`

Both exact-v308 classes preserve the enum constants NONE, PROTANOPE, DEUTERANOPE and
TRITANOPE. R387 therefore remains useful corroboration that the later GPU/plugin package
contains the same color-blind mode vocabulary, but the global Chat 2 semantic namespace
keeps the earlier R15 ownership and does not mint a second identical class semantic name.

The former R387 candidate/review/test are removed.

R387 remains a correction/audit batch only. Chat 2 performs no acceptance or rewrite.
