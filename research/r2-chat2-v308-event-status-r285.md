# Chat 2 — exact-v308 event status concrete helpers R285

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/L` -> `CLIENT_CLASS_000558` -> `EventActivityViewerRefreshTask`
- `rs/n/c/O` -> `CLIENT_CLASS_000561` -> `EventStatusOverviewInterface`
- `rs/n/c/P` -> `CLIENT_CLASS_000562` -> `EventStatusOverviewPacketHandler`
- existing R6: `rs/n/c/Q` -> `CLIENT_CLASS_000563` -> `EventBrawlStatusInterface`
- review: `SEMREVIEW_92EDF251E913F9596304`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 evidence

`EventActivityViewerRefreshTask` is registered by the retained `EventActivityViewerInterface` for interface 30072 at a 500 ms interval. Every run walks that interface's activity rows and refreshes the corresponding text widgets beginning at 30333.

`EventStatusOverviewInterface` is identified by its complete exact surface rather than one neighboring class. It presents the current hotspot and vote-to-skip status together with Dharok PK Tournament, Golden HG, Blood LMS, Event Brawl, Event Global Boss and Event Wildy Boss state, plus the exact actions **View Active Events** and **View all events**.

`EventStatusOverviewPacketHandler` extends the ScriptPacket handler base. Its seven exact selector branches mutate only the state consumed by that overview: hotspot timing/text, tournament state, Golden HG/Blood LMS timers, named global/wilderness boss timers and Event Brawl timing.

## Deliberate exclusions

R285 does not name `rs/n/c/R`, `rs/n/c/S`, or the generic `rs/n/b/**` scheduler hierarchy. Their mechanics are understood, but the surviving evidence is not yet strong enough to assign source-level nouns without overreach.

## Boundary

R285 is non-canonical research only. No semantic acceptance or source rewrite is performed.
