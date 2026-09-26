# Chat 2 — exact-v308 MemorizedNpc recovery R243

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/s/o/b` -> `CLIENT_CLASS_000942` -> `MemorizedNpc`
- confidence: **0.999**
- review: `SEMREVIEW_D66439477D22EAD9F9FA`
- unresolved: **0**
- field/method proposals: **0**

## Exact source match

The v308 class stores exactly the respawn-memory state used by RuneLite's NPC Indicators implementation:

- NPC index
- NPC name
- NPC size
- death tick
- respawn time
- possible respawn `WorldPoint` locations

Its constructor matches RuneLite `MemorizedNpc`: copy NPC name/index, allocate the respawn-location list with capacity **2**, initialize the two tick fields to **-1**, then copy transformed-composition size when available.

Historical source authority: RuneLite `MemorizedNpc` at `68c819924cfd6bfb4848c71f74c121109f289d5a`.

The adjacent `rs/s/o/c` highlight renderer is deliberately left unnamed here because it is a SpawnPK/forked per-NPC overlay path rather than the historical `NpcRespawnOverlay` class.

## Acceptance boundary

R243 remains non-canonical. Chat 2 performs no semantic acceptance.
