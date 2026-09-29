# Chat 2 — Ground Markers source identities R378

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/f/a` -> `CLIENT_CLASS_000907` -> `ColorTileMarker`
- `rs/s/f/b` -> `CLIENT_CLASS_000908` -> `GroundMarkerConfig`
- `rs/s/f/d` -> `CLIENT_CLASS_000910` -> `GroundMarkerPlugin`
- `rs/s/f/f` -> `CLIENT_CLASS_000912` -> `GroundMarkerPoint`
- review: `SEMREVIEW_DC5C1AE0FD4FA36363A9`

R188 already owns sibling `rs/s/f/c` as `GroundMarkerOverlay`.

Exact v308 preserves the `groundMarker` storage/config group, region-scoped marker
serialization, and menu actions Mark / Unmark / Label / Color / Reset color / Reset all.

Historical RuneLite Ground Markers source preserves all four recovered identifiers and the
same data/config/plugin roles.

`rs/s/f/e` is intentionally withheld: it is only the anonymous Gson
`TypeToken<List<GroundMarkerPoint>>` compiler/helper artifact.

R378 remains non-canonical semantic research only.
