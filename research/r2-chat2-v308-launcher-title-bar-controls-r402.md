# Chat 2 — launcher title-bar controls R402

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/O` -> `CLIENT_CLASS_000199` -> `LauncherTitleBarControlsPanel`
- `rs/gui/P` -> `CLIENT_CLASS_000200` -> `LauncherTitleBarControlsLayout`
- `rs/gui/A` -> `CLIENT_CLASS_000184` -> `LauncherTitleBarControlsPositioningLayout`

Review: `SEMREVIEW_4A980A07E435C0E99624`

## Exact title-pane registration

Launcher constructs `rs/gui/O` and marks it with the Substance property:

`substancelaf.internal.titlePane.extraComponentKind`

set to:

`SubstanceTitlePaneUtilities.ExtraComponentKind.TRAILING`

before inserting it into the live title pane.

The small launcher side-panel control button is added to this panel.

## Inner controls layout

`rs/gui/O` installs `rs/gui/P` as its LayoutManager2.

The layout computes:

- preferred/minimum/maximum width = `componentCount * 27`
- height = `23`

and lays controls left-to-right in 23-pixel cells with 4-pixel leading gaps and vertical
centering.

## Positioning wrapper

Launcher obtains the Substance title pane's existing layout manager and wraps it with
`rs/gui/A`.

On each layout:

1. delegate to the original title-pane layout;
2. measure the trailing controls panel;
3. place it at `titlePaneWidth - 75 - controlsWidth`;
4. keep it at y=0 with full title-pane height.

That fixes this class specifically as the positioning wrapper for the launcher's trailing
title-bar controls.

## Boundary

R402 remains non-canonical semantic research only.
