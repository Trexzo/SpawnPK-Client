# Chat 2 — NPC Indicators plugin R396 correction

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Corrected result

- `rs/s/o/e` -> `CLIENT_CLASS_000945` -> `NpcIndicatorsPlugin`
- proposal: `SEMPROP_58AF0A206F7EA87B06E6`
- review: `SEMREVIEW_522C412AEE140608E5CA`

## Duplicate correction

The first R396 attempt also proposed:

- `rs/s/o/d` -> `CLIENT_CLASS_000944` -> `NpcIndicatorsConfig`

After current Main was reconciled into the active Chat 2 continuation branch, the repository-wide
uniqueness gate correctly exposed that exact owner/name/stable-id as already authoritative in
**R4**:

- R4 proposal: `SEMPROP_3EA119C8462103D4B8A1`
- R4 review: `SEMREVIEW_DE8D18FF905B89D02488`

The duplicate config proposal has therefore been removed completely from R396.

## Retained plugin evidence

`rs/s/o/e` remains unowned by prior semantic reviews and extends the recovered plugin base.

It provides/consumes the already-authoritative R4 `NpcIndicatorsConfig`, owns the plugin
start/stop lifecycle, and coordinates R189 `NpcIndicatorsOverlay` together with the
HighlightedNpc/MemorizedNpc state family.

Surviving menu strings:

- `Tag`
- `Un-tag`
- `Tag-All`
- `Un-tag-All`

Surviving render-style literals:

- `hull`
- `tile`
- `truetile`
- `swtile`
- `swtruetile`
- `outline`

It subscribes to ConfigChanged, GameStateChanged, NpcSpawned and MenuHover.

## Boundary

R396 now retains exactly one non-canonical proposal. No semantic acceptance or source rewrite
is performed by Chat 2.
