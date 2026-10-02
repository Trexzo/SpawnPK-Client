# Chat 2 — InfoBox value identities R485

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Recovered exact-v308 source-style identities:

- `rs/ui/a/a` -> `CLIENT_CLASS_001017` -> `BoostInfoBox`
- `rs/ui/a/b` -> `CLIENT_CLASS_001018` -> `CounterInfoBox`
- `rs/ui/a/i` -> `CLIENT_CLASS_001025` -> `StatusInfoBox`
- `rs/ui/a/j` -> `CLIENT_CLASS_001026` -> `TimerInfoBox`

Review: `SEMREVIEW_87DCA8E01DE2EB648DC6`

Each identity is preserved directly by exact-v308 constant-pool/toString data and the class
behavior matches its role over the existing InfoBox base.

R485 remains non-canonical semantic research only.
