# Chat 2 — exact-v308 Tile Indicators overlay R190

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R190 is a separate non-canonical class-only review for the live overlay in the reviewed
Tile Indicators plugin package.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_6342E35B4E2884955FF4`
- field/method proposals: **0**

## Stable ID

`rs/s/r/b` -> `CLIENT_CLASS_000959` -> `TileIndicatorsOverlay`

## Exact render surface

R4 already recovered `TileIndicatorConfig`; R10 recovered `TileIndicatorsPlugin`.

The remaining live class stores only that config and renders exactly the three option groups
named by it:

- destination tile;
- hovered tile;
- current tile.

For each enabled group the overlay resolves the corresponding local tile and draws its polygon
using the group's configured highlight/fill colors and border width.

The current-tile branch resolves the local Player position; destination and hovered branches
use the client destination/hover coordinate state.

No unrelated interface or gameplay domain is rendered.

## Confidence boundary

`TileIndicatorsOverlay` is **0.999**.

The name is descriptive exact-behavior recovery grounded in the reviewed config/plugin pair
and the complete current/destination/hovered rendering surface.

## Acceptance boundary

R190 remains class-only and non-canonical. Main/Core may accept the proposal only through an
explicit `semantic_acceptance_spec` bound to `SEMREVIEW_6342E35B4E2884955FF4`.
