# Chat 2 — Material Tabs R492

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/ui/components/b/a` -> `CLIENT_CLASS_001060` -> `MaterialTab`
- `rs/ui/components/b/e` -> `CLIENT_CLASS_001064` -> `MaterialTabGroup`
- review: `SEMREVIEW_5789FBA171B6FB2F21B5`

Exact v308 matches RuneLite's Material Tabs UI pair directly. MaterialTab is the JLabel-backed
tab carrying one content component and optional BooleanSupplier selection gate. MaterialTabGroup
owns the display panel and List<MaterialTab>, adds/selects tabs and swaps selected content.

R490 TopLevelConfigPanel consumes this exact pair.

The sibling classes `rs/ui/components/b/b`, `c` and `d` are listener/helper
implementations and remain unnamed.

R492 remains non-canonical semantic research only.
