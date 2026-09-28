# Chat 2 — Launcher title-pane/window helpers R344

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/A` -> `CLIENT_CLASS_000184` -> `TitlePaneControlLayout`
- `rs/gui/O` -> `CLIENT_CLASS_000199` -> `TitlePaneControlPanel`
- `rs/gui/C` -> `CLIENT_CLASS_000186` -> `LauncherWindowResizableTask`
- `rs/gui/D` -> `CLIENT_CLASS_000187` -> `LauncherWindowSizeTask`
- review: `SEMREVIEW_686ABD66C7FB93794A1C`

## Title-pane control surface

Launcher obtains the Substance title-pane component and creates one `rs/gui/O` panel.
It marks that panel as the exact Substance **TRAILING** extra-component kind and adds the
button whose tooltip is:

`Hide/show side panel`

The button uses the panel/panel2 image assets and the existing sidebar visibility path.

Launcher then wraps the title pane's existing LayoutManager in `rs/gui/A`.
The wrapper delegates normal layout first, then pins the custom control panel using its
preferred width at:

`titlePaneWidth - 75 - panelWidth`

with full title-pane height.

That fixes the roles as a title-pane control panel and its positioning layout.

## Window EDT tasks

`rs/gui/C` is scheduled through `SwingUtilities.invokeLater` and its entire run method is:

- resolve Launcher's JFrame;
- call `setResizable(capturedBoolean)`.

`rs/gui/D` captures two width/height pairs and its run method:

- sets JFrame minimum size from pair 1;
- sets JFrame current size from pair 2.

## Withheld siblings

`rs/gui/B` is obsolete timer-listener scaffolding; the live Launcher uses an invokedynamic
ActionListener for that behavior.

`rs/gui/P` is installed by the `rs/gui/O` constructor but immediately replaced by
GridBagLayout in the live Launcher setup, so it is not promoted from dead/overwritten
layout behavior.

R344 remains non-canonical semantic research only.
