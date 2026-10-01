# Chat 2 — exact-v308 World Tournament and Knowledgebase interfaces R446

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/aX` -> `CLIENT_CLASS_000599` -> `WorldTournamentInterface`
- `rs/n/c/ba` -> `CLIENT_CLASS_000639` -> `SpawnPKKnowledgebaseInterface`
- review: `SEMREVIEW_2D532CDC053C5858C574`

## WorldTournamentInterface

This is the main World Tournament screen and is distinct from R445's separate leaderboard screen.

Exact literals/resources include:

- `<img=128> SpawnPK World Tournaments <img=128>`
- `Next world tournament: @yel@Dharok PK Tournament`
- `This tournament's prize will be..`
- `@yel@Previous Tournament Winners`
- `@yel@Tournament point shop`
- `Enter Tournament <img=51>`
- `Spectate Tournament`
- `View tournament shop`
- `tournament/sprite`
- `tournament/sprite 0`

## SpawnPKKnowledgebaseInterface

Exact literals/state include:

- `Official SpawnPK Knowledgebase`
- `Category List`
- `Selected Article Title Text`
- `Go back`
- `Select option`
- `WIKI_SELECTED_`
- `wiki/sprite 0`

The class also owns category/article population helpers and explicit category/description overflow guards.

## Boundary

Both names identify client presentation surfaces only. Tournament scheduling/rewards and
knowledgebase content authority remain outside this semantic recovery.

R446 remains non-canonical Chat 2 research only.
