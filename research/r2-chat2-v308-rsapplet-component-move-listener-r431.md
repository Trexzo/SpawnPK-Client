# Chat 2 — exact-v308 RSApplet component-move listener R431

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/D` -> `CLIENT_CLASS_000031` -> `RSAppletComponentMoveListener`
- proposal: `SEMPROP_CC9EE7B9A7F3E3629B1F`
- review: `SEMREVIEW_CF3FF129C054BB1845DC`

R48 already recovers the surrounding `RSApplet` / `RSFrame` shell.

Exact v308 constructs `rs/D` from RSApplet and registers it through
`Component.addComponentListener`.

The class extends `ComponentAdapter` and implements one callback only:
`componentMoved(ComponentEvent)`.

Move events are throttled to a 100 ms window. When accepted, the listener flips the
client-global move/redraw marker and updates the previous-move timestamp.

The semantic name stops at the exact event role; it does not guess a stronger downstream
layout or persistence responsibility.

R431 remains non-canonical Chat 2 research only.
