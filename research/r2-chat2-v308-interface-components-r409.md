# Chat 2 — source-proven interface components R409

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R406 recovered the source-proven Widget/WidgetManager roots. R283/R284 already own the
dropdown and layout internals. R409 fills the six source-proven component classes that sit
between those layers:

- `rs/n/a/a` / 000526 -> `SpriteComponent`
- `rs/n/a/b` / 000532 -> `OverlayComponent`
- `rs/n/a/c` / 000533 -> `InventoryComponent`
- `rs/n/a/d` / 000534 -> `LayoutComponent`
- `rs/n/a/e` / 000535 -> `ImageButtonComponent`
- `rs/n/a/f` / 000536 -> `TextComponent`

Review: `SEMREVIEW_3FED2798F5BA838303AB`

Exact-v308 bytecode independently matches each recovered source role: sprite factories and
hover sprites, overlay specialization, inventory-grid state, R284 layout-manager delegation,
image-button state and fluent text/font/alignment configuration.

No dropdown/layout classes are duplicated here.

R409 remains non-canonical semantic research only.
