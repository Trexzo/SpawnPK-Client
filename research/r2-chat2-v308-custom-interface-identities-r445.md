# Chat 2 — exact-v308 custom interface identities R445

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Corrected result

- `rs/n/c/aU` -> `CLIENT_CLASS_000596` -> `TeleportSelectionInterface`
- `rs/n/c/aW` -> `CLIENT_CLASS_000598` -> `WorldTournamentLeaderboardsInterface`
- review: `SEMREVIEW_45AF2113C6C4B028B8E1`

The original R445 also repeated:

- `rs/n/c/aS` -> `CLIENT_CLASS_000594` -> `TaskScrollInterface`

That exact owner, stable ID, semantic name and proposal ID were already owned by R5.
The duplicate row is therefore removed from R445 rather than renamed or re-proposed.

## TeleportSelectionInterface

Exact resources/literals include:

- `teleport/SPRITE`
- `Teleport`
- `Teleport <img=149>`
- `Title of Location`
- `Select this teleport`

The class also owns the helper that populates selectable teleport rows into the scroll area.

## WorldTournamentLeaderboardsInterface

Exact literals include:

- `World Tournament Leaderboards`
- `<img=14> Top Players`
- `<img=16> Top Clans`
- `This week`
- `All time`
- `View weekly leaderboard`
- `View all time leaderboard`

The builder owns separate large list surfaces for player and clan rankings.

## Boundary

R5 remains the sole Chat 2 semantic owner of `TaskScrollInterface`.

R445 retains only the two genuinely new custom-interface identities and remains
non-canonical Chat 2 research.
