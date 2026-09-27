# Chat 2 — exact-v308 typed RSInterface widget builders R289

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/a/c` -> `CLIENT_CLASS_000533` -> `InventoryGridWidget`
- `rs/n/a/d` -> `CLIENT_CLASS_000534` -> `InterfaceContainerWidget`
- `rs/n/a/e` -> `CLIENT_CLASS_000535` -> `SpriteWidget`
- `rs/n/a/f` -> `CLIENT_CLASS_000536` -> `TextWidget`
- review: `SEMREVIEW_5A8DDACCA8BF31F8F3F5`
- unresolved: **0**
- member proposals: **0**

`InventoryGridWidget` sets exact RSInterface type 2 and owns the item/amount/slot arrays consumed by inventory rendering.

`InterfaceContainerWidget` owns child arrays, dimensions/scroll state and the retained `InterfaceLayoutManager`, then commits resolved child positions to the owning interface.

`SpriteWidget` sets exact RSInterface type 5 and owns sprite state and dimensions.

`TextWidget` sets exact RSInterface type 4 and owns text/font/color/alignment/shadow/action configuration.

`rs/n/a/a` and `rs/n/a/b` remain excluded for a separate clickable/hover-sprite pass.

R289 is non-canonical semantic research only. No acceptance, source rewrite or source materialization is performed.
