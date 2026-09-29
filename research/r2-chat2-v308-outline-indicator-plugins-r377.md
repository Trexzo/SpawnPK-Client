# Chat 2 — outline/indicator plugin source identities R377

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/p/a` -> `CLIENT_CLASS_000946` -> `PlayerOutlineConfig`
- `rs/s/p/d` -> `CLIENT_CLASS_000949` -> `PlayerOutlinePlugin`
- `rs/s/r/a` -> `CLIENT_CLASS_000958` -> `TileIndicatorsConfig`
- `rs/s/r/c` -> `CLIENT_CLASS_000960` -> `TileIndicatorsPlugin`
- `rs/s/i/a` -> `CLIENT_CLASS_000919` -> `InteractHighlightConfig`
- `rs/s/i/c` -> `CLIENT_CLASS_000921` -> `InteractHighlightPlugin`
- review: `SEMREVIEW_932079B2E27F3998F1C9`

## Player Outline

R187 already recovered `PlayerOutlineOverlay` and `PetOutlineOverlay`.
Exact v308 preserves the `playeroutline` configuration vocabulary and the distinctive
Player Outline plugin descriptor. Historical Meteor/RuneLite-derived source preserves
`PlayerOutlineConfig` and `PlayerOutlinePlugin`; v308 adds a pet-outline toggle.

## Tile Indicators

R190 already recovered `TileIndicatorsOverlay`.
Exact v308 preserves Current Tile / Destination Tile configuration and the descriptor
`Highlight the tile you are currently moving to`. Historical RuneLite source preserves
`TileIndicatorsConfig` and `TileIndicatorsPlugin`.

## Interact Highlight

R191 already recovered `InteractHighlightOverlay`.
Exact v308 preserves `interacthighlight` configuration for NPC/object hover/interact
outlines and the descriptor `Outlines npcs and objects you interact with or hover over`.
Historical RuneLite source preserves `InteractHighlightConfig` and
`InteractHighlightPlugin`.

## Boundary

These are source-lineage/source-name recoveries. Exact-v308 custom extensions remain primary
authority. R377 remains non-canonical semantic research only.
