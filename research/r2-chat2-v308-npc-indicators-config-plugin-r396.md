# Chat 2 — NPC Indicators config/plugin R396

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/o/d` -> `CLIENT_CLASS_000944` -> `NpcIndicatorsConfig`
- `rs/s/o/e` -> `CLIENT_CLASS_000945` -> `NpcIndicatorsPlugin`
- review: `SEMREVIEW_C23637876E37D362B0D6`

The stable IDs come from exact `seed_lineage()` ordering across the complete `rs/`
namespace, cross-checked against the adjacent already-reviewed family:

- 000940 `HighlightedNpc`
- 000941 `HighlightedNpcBuilder`
- 000942 `MemorizedNpc`
- 000943 `NpcIndicatorsOverlay`
- 000944 config
- 000945 plugin

## Configuration

`rs/s/o/d` is a config interface with the surviving exact group literal:

`npcindicators`

Its options cover indicator enablement, tag/name state, colors, fill/outline behavior,
border width and rendering style.

## Plugin

`rs/s/o/e` extends the recovered plugin base and owns the full NPC Indicators lifecycle.

Surviving menu strings:

- `Tag`
- `Un-tag`
- `Tag-All`
- `Un-tag-All`

Surviving render-style literals include:

- `hull`
- `tile`
- `truetile`
- `swtile`
- `swtruetile`
- `outline`

It subscribes to ConfigChanged, GameStateChanged, NpcSpawned and MenuHover and manages the
already-recovered HighlightedNpc/MemorizedNpc/NpcIndicatorsOverlay family.

Earlier Chat 2 research had identified these names informally, but no surviving semantic
candidate/review batch owned these exact stable coordinates. R396 makes that evidence
deterministic without duplicating another review target.

R396 remains non-canonical semantic research only.
