# Chat 2 — Ground Marker config/plugin completion R483

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/f/b` -> `CLIENT_CLASS_000908` -> `GroundMarkerConfig`
- `rs/s/f/d` -> `CLIENT_CLASS_000910` -> `GroundMarkerPlugin`
- review: `SEMREVIEW_09194F2FA33A34EFF111`

Existing family authority:

- R482 `rs/s/f/a` -> `ColorTileMarker`
- R188 `rs/s/f/c` -> `GroundMarkerOverlay`
- R482 `rs/s/f/f` -> `GroundMarkerPoint`

## GroundMarkerConfig

The exact interface preserves:

- config group `groundMarker`
- key `showImportExport`
- default marker color
- label/render toggles
- border width
- fill opacity

R188 GroundMarkerOverlay consumes those values directly. Historical RuneLite
`GroundMarkerConfig` carries the same config constants and settings contract.

## GroundMarkerPlugin

The exact class owns the live marker collection and the full interaction/persistence loop:

- mark/unmark context-menu entries;
- `Reset color` and `Pick color`;
- per-marker color choices;
- `region_<id>` JSON persistence under `groundMarker`;
- persisted `GroundMarkerPoint` <-> live `ColorTileMarker` conversion;
- WorldPoint reconstruction and instance expansion.

Historical RuneLite `GroundMarkerPlugin` matches this structure directly.

## Withheld helper

`rs/s/f/e` remains unnamed. It is only the plugin's anonymous Gson
`TypeToken<List<GroundMarkerPoint>>` helper and has no independent semantic identity worth
inventing.

R483 remains non-canonical semantic research only.
