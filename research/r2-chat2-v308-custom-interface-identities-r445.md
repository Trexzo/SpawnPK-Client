# Chat 2 — exact-v308 custom interface identities R445

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/aS` -> `CLIENT_CLASS_000594` -> `TaskScrollInterface`
- `rs/n/c/aU` -> `CLIENT_CLASS_000596` -> `TeleportSelectionInterface`
- `rs/n/c/aW` -> `CLIENT_CLASS_000598` -> `WorldTournamentLeaderboardsInterface`
- review: `SEMREVIEW_B075370A772D4CA71B4E`

All three classes directly extend R436 `CustomInterfaceBuilder` and are live registry entries.

## TaskScrollInterface

Exact literals/resources include:

- `@or1@Task Scroll Title`
- `@or1@Task Information`
- `@or1@Potential Rewards`
- `@or1@Completion Progress`
- `tasks/SPRITE`
- `tasks/SPRITE 2`
- `Collect reward`
- `Track progress`
- `0% (0/100)`

The progress tooltip explicitly explains objective completion and casket reward presentation.

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

These are client presentation identities only. No task completion rules, teleport eligibility,
tournament ranking computation or server reward authority is inferred.

R445 remains non-canonical Chat 2 research only.
