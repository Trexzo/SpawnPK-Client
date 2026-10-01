# Chat 2 R3 — title-pane control panel layout R361

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

- `rs/gui/P` -> `CLIENT_CLASS_000200` -> `TitlePaneControlPanelLayout`
- proposal: `SEMPROP_3B0C05DB64DE0C3A4997`
- review: `SEMREVIEW_31F977711005E31BA522`

R344 already recovered `rs/gui/O` as `TitlePaneControlPanel`. O constructs exactly one
`rs/gui/P` and installs it as its layout manager.

P implements `LayoutManager2`, computes a compact single-row size from component count and
lays child controls horizontally in fixed-height cells. All unrelated layout hooks are no-ops.

R361 is descriptive non-canonical semantic research only.
