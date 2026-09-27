# Chat 2 — exact-v308 InfoBox concrete family R267

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/ui/a/a` -> `CLIENT_CLASS_001017` -> `BoostInfoBox`
- `rs/ui/a/b` -> `CLIENT_CLASS_001018` -> `CounterInfoBox`
- `rs/ui/a/f` -> `CLIENT_CLASS_001022` -> `InfoBoxManager`
- `rs/ui/a/i` -> `CLIENT_CLASS_001025` -> `StatusInfoBox`
- `rs/ui/a/j` -> `CLIENT_CLASS_001026` -> `TimerInfoBox`
- review: `SEMREVIEW_A3DAE64925416FF5BE45`
- unresolved: **0**
- field/method proposals: **0**

## Exact identities

Three SpawnPK-specific concrete nouns survive directly in generated `toString` recipes:

- `BoostInfoBox(offset=…, skillId=…)`
- `CounterInfoBox(count=…)`
- `StatusInfoBox(EMPTY=…)`

The timer likewise self-identifies as:

- `TimerInfoBox(startTime=…, endTime=…, duration=…)`

The exact timer bytecode independently preserves the positive-period guard
`negative period!`, start/end/duration state, 10% red threshold, expiry render/cull behavior,
and duration mutation paths.

## InfoBoxManager

`rs/ui/a/f` owns the full reviewed InfoBox/InfoBoxOverlay lifecycle. Exact v308 preserves:

- `Default Group`
- `InfoBoxOverlay`
- `infoboxgroup`
- `infoboxoverlay`
- `orient_`
- `Detach InfoBox`
- `Flip`
- `Delete`
- add/remove/move/merge InfoBox log messages

Its layer map, sorting, image scaling, layer persistence, orientation persistence,
split/merge behavior, and overlay registration match RuneLite InfoBoxManager.

## Deliberate exclusions

- `rs/ui/a/c` = already reviewed `InfoBox`
- `rs/ui/a/d` = already reviewed `InfoBoxComponent`
- `rs/ui/a/e` = already reviewed `InfoBoxSpriteType`
- `rs/ui/a/g` = already reviewed `InfoBoxOverlay`
- `rs/ui/a/h` = already reviewed `InfoBoxPriority`

R267 therefore fills only the remaining live InfoBox-domain classes in this package.

## Acceptance boundary

R267 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
