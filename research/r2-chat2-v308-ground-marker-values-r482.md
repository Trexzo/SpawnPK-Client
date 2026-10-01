# Chat 2 — exact-v308 Ground Marker value types R482

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/f/a` -> `CLIENT_CLASS_000907` -> `ColorTileMarker`
- `rs/s/f/f` -> `CLIENT_CLASS_000912` -> `GroundMarkerPoint`
- review: `SEMREVIEW_AABB42D4F7188E670787`

## ColorTileMarker

Exact `toString` identity:

`ColorTileMarker(worldPoint=..., color=..., label=...)`

The final class contains only:

- WorldPoint
- nullable Color
- nullable label

R188 GroundMarkerOverlay already independently proves this exact class is the live marker
value type rendered by the Ground Marker feature.

## GroundMarkerPoint

Exact `toString` identity:

`GroundMarkerPoint(regionId=..., regionX=..., regionY=..., z=..., color=..., label=...)`

Ground Marker plugin stores collections of these records as JSON under:

- config group `groundMarker`
- key `region_<regionId>`

It reconstructs a WorldPoint from the four coordinate fields and creates ColorTileMarker
using the same color and label.

Thus exact v308 cleanly separates:

- persisted marker record: `GroundMarkerPoint`
- live overlay marker: `ColorTileMarker`

## Stable IDs

Sorted exact-v308 `rs/**` order gives:

- `rs/s/f/a` -> 907
- R188 `rs/s/f/c` -> 909
- `rs/s/f/f` -> 912

R482 remains non-canonical semantic research only.
