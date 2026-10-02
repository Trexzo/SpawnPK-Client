# Chat 2 — InfoBox residual identities R485

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R485 retains two genuinely new proposals:

- `rs/ui/a/b` -> `CLIENT_CLASS_001018` -> `CounterInfoBox`
- `rs/ui/a/i` -> `CLIENT_CLASS_001025` -> `StatusInfoBox`

Review: `SEMREVIEW_CE764AB3A4FDFFEF8646`

The same exact-v308 literal scan also independently recovered `BoostInfoBox` and
`TimerInfoBox`, but R12 already owns those exact classes with the same proposal IDs.
They were removed from R485 rather than duplicated.

R485 remains non-canonical semantic research only.
