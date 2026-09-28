# Chat 2 — exact-v308 scene polygon registry / ScriptPacket 12 R133

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R133 is a separate non-canonical class-only review for the exact scene-polygon record,
live registry and ScriptPacket add/remove controller.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_ECFD89E822D82DB15FA6`
- field/method proposals: **0**

## Stable IDs

- `rs/l/e/n` -> `CLIENT_CLASS_000435` -> `ScenePolygonRecord`
- `rs/l/e/o` -> `CLIENT_CLASS_000436` -> `ScenePolygonManager`
- `rs/l/e/p` -> `CLIENT_CLASS_000437` -> `ScenePolygonPacketHandler`

## ScenePolygonRecord

`rs/l/e/n` owns:

- one `java.awt.Polygon`;
- one fill `java.awt.Color`;
- one outline `java.awt.Color`;
- one optional String;
- two integer source coordinates.

Its exact factories establish two scene-geometry modes.

One factory accepts an entity and obtains that entity's live scene polygon/hull.

The other accepts tile x/y plus fill/outline colors, converts the tile relative to
`Client.eh` / `Client.ei` into the client scene coordinate system, obtains the
corresponding Polygon from Client, and stores the original tile coordinates so the Polygon
can be recomputed later.

Because the class can represent both entity hulls and world-tile geometry, R133 deliberately
uses the broader noun `ScenePolygonRecord` instead of a tile-only name.

## ScenePolygonManager

`rs/l/e/o` owns both:

- `Map<String, rs/l/e/n>`;
- `List<rs/l/e/n>`.

It exposes add/update/remove operations for polygon records, including coordinate-keyed tile
entries.

Exact Client initialization constructs one manager instance into:

`Client.aa`

This is not a dead helper. The scene renderer `rs/l/b/c` checks both collections on
`Client.aa`, creates a scene `Graphics2D`, and renders every non-null record through:

`rs/C.a(Graphics2D, Polygon, fillColor, outlineColor)`

That direct renderer join fixes the manager and record as scene-polygon state.

## ScriptPacket 12

R115 registers ScriptPacket **12** from `rs/l/e/o.a`.

Exact v308 initializes that field with:

`new rs/l/e/p()`

The handler implements two selector modes.

### Selector 0 — add/replace

It reads:

1. four integers forming one RGBA Color;
2. four integers forming a second RGBA Color;
3. tile x;
4. tile y.

It uses the live `Client.aa` manager, builds the coordinate key and adds/replaces the
tile-coordinate polygon record with those exact fill/outline colors.

It then reads one integer. When that value is 1, one additional packet String is read and
stored on the record.

R133 preserves that as an optional packet String only; the renderer evidence used here does
not justify assigning a narrower label/text semantic role to that field.

### Selector 1 — remove

It reads tile x/y and removes the matching coordinate-keyed polygon from the same manager.

No branch mutates another subsystem.

## Naming boundary

All three names are descriptive readable recovery names, not original source-identifier
claims.

`ScenePolygonRecord` and `ScenePolygonManager` are **0.997** because their exact state and
scene-renderer roles are proven while the original class nouns are stripped.

`ScenePolygonPacketHandler` is **0.998** because exact ScriptPacket registration and its
complete add/remove protocol additionally bind the handler to this subsystem.

## Acceptance boundary

Chat 2 does not promote R133. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_ECFD89E822D82DB15FA6`.
