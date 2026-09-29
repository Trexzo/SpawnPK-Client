# Chat 2 — vote, duel, emotes and PK leaderboard interfaces R385

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result
- `rs/n/c/M` -> `CLIENT_CLASS_000559` -> `VoteRewardsInterface`
- `rs/n/c/E` -> `CLIENT_CLASS_000550` -> `DuelTypeSelectionInterface`
- `rs/n/c/F` -> `CLIENT_CLASS_000551` -> `EmotesInterface`
- `rs/n/c/Z` -> `CLIENT_CLASS_000572` -> `PkLeaderboardsInterface`
- review: `SEMREVIEW_CE1529DEF5F59020C8AC`

All four identities are fixed directly by exact-v308 visible UI vocabulary and their complete widget surfaces. No vote verification, duel rules, emote server behavior or leaderboard publication authority is inferred. R385 remains non-canonical.
