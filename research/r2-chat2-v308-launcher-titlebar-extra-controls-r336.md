# Chat 2 continuation — Launcher title-bar extra controls R336

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/A` -> `CLIENT_CLASS_000184` -> `LauncherTitleBarExtraControlsLayout`
- `rs/gui/O` -> `CLIENT_CLASS_000199` -> `LauncherTitleBarExtraControlsPanel`
- review: `SEMREVIEW_8805027A68F87B17DA49`

## Title-bar controls panel

Launcher constructs `rs/gui/O`, marks it with the exact Substance title-pane property:

`substancelaf.internal.titlePane.extraComponentKind = TRAILING`

and adds it directly into the Substance title-pane component.

In the normal client path the panel contains the exact 23x22 side-panel toggle button with
tooltip:

`Hide/show side panel`

whose action is already R280 `SidePanelToggleAction`.

## Title-pane layout wrapper

Launcher saves the title pane's original LayoutManager and wraps it with `rs/gui/A`.

The wrapper delegates normal layout behavior first, then reads the preferred width of the
extra-controls panel and pins it at:

`x = titlePaneWidth - 75 - panelWidth`

with y=0 and full title-pane height.

## Withheld legacy layout

`rs/gui/P` is installed by `rs/gui/O`'s constructor but the live Launcher path immediately
replaces it with GridBagLayout before the title-bar panel is used. P remains intentionally
unnamed as legacy/dead layout code.

R336 remains non-canonical semantic research only.
