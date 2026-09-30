# Chat 2 successor — exact-v308 interface builders R373

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/Z` -> `CLIENT_CLASS_000572` -> `PkLeaderboardSelectionInterface`
- `rs/n/c/E` -> `CLIENT_CLASS_000550` -> `DuelTypeSelectionInterface`
- `rs/n/c/M` -> `CLIENT_CLASS_000559` -> `VotingRewardsInterface`
- `rs/n/c/ak` -> `CLIENT_CLASS_000612` -> `BountyTeleportInterface`
- `rs/n/c/aE` -> `CLIENT_CLASS_000580` -> `LegendaryPetFusingInterface`
- review: `SEMREVIEW_60430283D4C6B00CCB9E`

All five classes extend the exact interface-builder base `rs/n/c` and expose only deterministic
widget construction.

## Withheld neighbor

`rs/n/c/aa` is intentionally not proposed. Exact v308 proves that it augments a gameframe
surface with Achievement Diary, Monster drop tables and hotspot state, but that mixed surface
does not preserve one sufficiently precise feature noun.

R373 remains non-canonical semantic research only.
