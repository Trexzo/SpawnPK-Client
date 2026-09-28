# Chat 2 — unique player-option packets R328

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/o/a/a/a/T` -> `CLIENT_CLASS_000732` -> `PlayerOption2Packet` (opcode 153)
- `rs/o/a/a/a/r` -> `CLIENT_CLASS_000704` -> `PlayerOption3Packet` (opcode 73)
- review: `SEMREVIEW_6587401478FB9847340D`

Exact-current protocol authority defines player options 1..5 as:

- 1 -> 128
- 2 -> 153
- 3 -> 73
- 4 -> 139
- 5 -> 39

R328 names only the unique generated packet classes for options 2 and 3.

## Duplicate boundary

Exact v308 contains duplicate generated serializer classes for:

- opcode 128: `rs/o/a/a/a/V` and `rs/o/a/a/a/e`
- opcode 139: `rs/o/a/a/a/Y` and `rs/o/a/a/a/f`

There is no exact-current evidence that distinguishes one duplicate as the canonical semantic
owner, so options 1 and 4 remain intentionally unresolved in this generated layer.

## Context boundary

S2C104 configures arbitrary player-option labels. Therefore these packet names describe the
transport slot only and do not claim verbs such as Follow, Trade, Challenge or Attack.

R328 remains non-canonical semantic research only.
