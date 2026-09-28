# Chat 2 — exact-v308 self-identifying support semantics R19

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R19 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R18 review batches.

## Deterministic review result

- candidate classes: **12**
- resolved proposals: **12**
- unresolved: **0**
- review ID: `SEMREVIEW_402B4C2AA42205916457`
- field/method proposals: **0**

## Asset icon cache

- `rs/A/a` -> `AssetIconManager`
- `rs/A/a$a` -> `AssetIconItemKey`
- `rs/A/a$b` -> `AssetIconSpriteKey`

The nested key classes literally self-identify as
`AssetIconManager.ItemKey(...)` and `AssetIconManager.SpriteKey(...)`.
The outer class owns the matching expiring caches and renders/caches item and sprite icon
images.

## UI/support values

- `rs/n/a/a/d` -> `DropDownOption`
- `rs/ui/a/b` -> `CounterInfoBox`
- `rs/ui/a/i` -> `StatusInfoBox`
- `rs/ui/l$a` -> `NavigationButtonBuilder`

Exact surviving toString forms include:

- `DropDownOption(text=…, tooltip=…)`
- `CounterInfoBox(count=…)`
- `StatusInfoBox(EMPTY=…)`
- `NavigationButton.NavigationButtonBuilder(icon=…, tab=…, tooltip=…, …)`

The builder constructs the already reviewed NavigationButton directly.

## Ground markers

- `rs/s/f/a` -> `ColorTileMarker`
- `rs/s/f/f` -> `GroundMarkerPoint`

Exact self-identifying forms preserve both names and their field roles:

- `ColorTileMarker(worldPoint=…, color=…, label=…)`
- `GroundMarkerPoint(regionId=…, regionX=…, regionY=…, z=…, color=…, label=…)`

## Developer-tools widget overlay

- `rs/s/c/e` -> `DevToolsWidgetOverlay`
- `rs/s/c/e$a` -> `DevToolsWidgetDisplay`

The nested record literally identifies itself as
`DevToolsWidgetOverlay.WidgetDisplay(text=…, x=…, y=…, type=…)`.
The outer overlay consumes DeveloperToolsConfig and builds queues of those display records.

## World coordinates

- `rs/runelite/a/p` -> `WorldPoint`

The exact self-identifying form is `WorldPoint(x=…, y=…, plane=…)`. The immutable value
also performs x/y/plane transforms and local/world coordinate conversion.

## Acceptance boundary

Chat 2 does not promote R19. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_402B4C2AA42205916457`.
