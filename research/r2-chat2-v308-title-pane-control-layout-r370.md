# Chat 2 — title-pane control layout R370

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/P` -> `CLIENT_CLASS_000200` -> `TitlePaneControlPanelLayout`
- proposal: `SEMPROP_3B0C05DB64DE0C3A4997`
- review: `SEMREVIEW_31F977711005E31BA522`

R344 already fixes `rs/gui/O` as `TitlePaneControlPanel`.

Its constructor creates exactly one `rs/gui/P` and installs it as the panel layout manager.

The layout:

- implements `LayoutManager2`;
- reports preferred width as `componentCount * 27`;
- reports height 23;
- gives each child a 23px-wide cell;
- advances horizontally with a 4px lead gap;
- caps child height at 23 and vertically centers shorter controls.

No gameplay/network/application state is owned.

## Boundary

This is a descriptive exact-v308 Swing role and does not claim the original stripped source
identifier. R370 remains non-canonical Chat 2 semantic research only.
