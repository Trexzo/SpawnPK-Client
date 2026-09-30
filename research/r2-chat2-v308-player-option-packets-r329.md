# Chat 2 continuation — player option packets R329

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/o/a/a/a/T` -> `CLIENT_CLASS_000732` -> `PlayerOption2Packet`
- `rs/o/a/a/a/r` -> `CLIENT_CLASS_000704` -> `PlayerOption3Packet`
- review: `SEMREVIEW_384B325C5FBA31E9601E`

## Why only slots 2 and 3

Exact-current player-option transport is:

1. 128
2. 153
3. 73
4. 139
5. 39

Exact v308 contains duplicate generated packet classes for opcodes 128 and 139, so Chat 2
does not arbitrarily choose one duplicate as the semantic owner of player option slots 1 or 4.

There is no generated opcode-39 packet object in this family.

Opcode 153 and opcode 73 each have exactly one generated packet object, so slots 2 and 3 are
safe to recover.

## Boundary

The names identify transport slots only. S2C104 can configure arbitrary player-option text,
so no historical verb such as Follow, Trade or Challenge is baked into these semantic names.

R329 remains non-canonical semantic research only.
