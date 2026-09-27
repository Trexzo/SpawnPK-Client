# Chat 2 — exact-v308 InfoBox concrete family R267

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/ui/a/a` -> `CLIENT_CLASS_001017` -> `BoostInfoBox`
- `rs/ui/a/b` -> `CLIENT_CLASS_001018` -> `CounterInfoBox`
- `rs/ui/a/i` -> `CLIENT_CLASS_001025` -> `StatusInfoBox`
- `rs/ui/a/j` -> `CLIENT_CLASS_001026` -> `TimerInfoBox`
- review: `SEMREVIEW_87DCA8E01DE2EB648DC6`
- unresolved: **0**
- field/method proposals: **0**

## Exact identities

All four names survive directly in exact-v308 generated `toString` recipes:

- `BoostInfoBox(offset=…, skillId=…)`
- `CounterInfoBox(count=…)`
- `StatusInfoBox(EMPTY=…)`
- `TimerInfoBox(startTime=…, endTime=…, duration=…)`

`BoostInfoBox` stores the skill id and current offset, renders a leading plus sign for
positive boosts, and selects its text color from the offset sign.

`CounterInfoBox` stores one count, renders blank for the exact sentinel value `-1`,
otherwise renders the decimal count, and uses white text.

`StatusInfoBox` is an image/status-only InfoBox specialization whose text is empty and
whose text color is white.

`TimerInfoBox` independently preserves the full timer contract: positive-period validation
with `negative period!`, start/end/duration state, minute/hour formatting, the final-10%
red threshold, expiry render/cull behavior, and duration mutation guarded by
`negative duration`.

RuneLite's historical Timer/Counter InfoBox family independently corroborates those exact
behavioral roles, while SpawnPK's own generated strings preserve the suffixed class nouns.

## Existing authority deliberately excluded

`rs/ui/a/f` / `CLIENT_CLASS_001022` is already reviewed in **R11** as
`InfoBoxManager` under review `SEMREVIEW_688BC62BD168440903CD`.

The first R267 draft rediscovered that same owner/name with stronger source-parity evidence.
The overlap guard correctly rejected it. R267 therefore does not duplicate or supersede R11.

Other existing InfoBox owners remain unchanged:

- `rs/ui/a/c` -> `InfoBox`
- `rs/ui/a/d` -> `InfoBoxComponent`
- `rs/ui/a/e` -> `InfoBoxSpriteType`
- `rs/ui/a/g` -> `InfoBoxOverlay`
- `rs/ui/a/h` -> `InfoBoxPriority`

## Acceptance boundary

R267 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
