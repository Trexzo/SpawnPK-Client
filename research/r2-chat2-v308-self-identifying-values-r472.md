# Chat 2 — exact-v308 self-identifying value classes R472

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/j/b/b` -> `CLIENT_CLASS_000309` -> `CustomMenuEntry`
- `rs/n/a/a/d` -> `CLIENT_CLASS_000530` -> `DropDownOption`
- `rs/s/c/e$a` -> `CLIENT_CLASS_000892` -> `DevToolsWidgetOverlayWidgetDisplay`
- `rs/s/f/a` -> `CLIENT_CLASS_000907` -> `ColorTileMarker`
- `rs/s/f/f` -> `CLIENT_CLASS_000912` -> `GroundMarkerPoint`
- `rs/runelite/a/j$c` -> `CLIENT_CLASS_000821` -> `RectangleUnionRectangle`
- `rs/runelite/a/p` -> `CLIENT_CLASS_000832` -> `WorldPoint`
- review: `SEMREVIEW_12B3FFC3AA42BACE2872`

Every identity is preserved directly by exact-v308 generated value-object metadata:

- `CustomMenuEntry(text=..., event=...)`
- `DropDownOption(text=..., tooltip=...)`
- `DevToolsWidgetOverlay.WidgetDisplay(text=..., x=..., y=..., type=...)`
- `ColorTileMarker(worldPoint=..., color=..., label=...)`
- `GroundMarkerPoint(regionId=..., regionX=..., regionY=..., z=..., color=..., label=...)`
- `RectangleUnion.Rectangle(x1=..., y1=..., x2=..., y2=...)`
- `WorldPoint(x=..., y=..., plane=...)`

Historical RuneLite/OpenOSRS source independently corroborates the ground-marker,
RectangleUnion and WorldPoint identities.

Nested source identities are flattened only because semantic names must be one Java
identifier.

R472 remains non-canonical semantic research only.
