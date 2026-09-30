# Chat 2 — exact-v308 launcher title-pane helpers R382

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/A` -> `CLIENT_CLASS_000184` -> `LauncherTitlePaneLayout`
- `rs/gui/B` -> `CLIENT_CLASS_000185` -> `LauncherSidePanelRepaintTimerAction`
- `rs/gui/C` -> `CLIENT_CLASS_000186` -> `LauncherResizableUpdateTask`
- `rs/gui/D` -> `CLIENT_CLASS_000187` -> `LauncherFrameSizeUpdateTask`
- `rs/gui/O` -> `CLIENT_CLASS_000199` -> `LauncherTitlePaneExtraPanel`
- `rs/gui/P` -> `CLIENT_CLASS_000200` -> `LauncherTitlePaneExtraLayout`
- `rs/gui/y` -> `CLIENT_CLASS_000286` -> `LauncherTrayRestoreMouseListener`
- `rs/gui/z` -> `CLIENT_CLASS_000287` -> `ToggleSidePanelAction`

Review: `SEMREVIEW_8352F2716C69A7A33FBC`

## Title-pane family

Launcher creates `rs/gui/O` and mounts it into the Substance title pane with:

`substancelaf.internal.titlePane.extraComponentKind = TRAILING`.

The panel hosts the exact button with tooltip:

`Hide/show side panel`

and owns `rs/gui/P`, a compact LayoutManager2 using a 23-pixel title-bar height.

Launcher then wraps the title pane's existing LayoutManager with `rs/gui/A`.
The wrapper delegates the original layout first and subsequently positions the trailing
extra panel against the right edge.

## EDT frame-update tasks

`rs/gui/C` captures one boolean and its run() calls JFrame.setResizable.

`rs/gui/D` captures four dimensions and its run() applies minimum and current JFrame
sizes.

Launcher submits both through SwingUtilities.invokeLater.

## Side-panel/tray helpers

`rs/gui/B` is a one-shot Timer listener. It conditionally repaints the launcher sidebar
unless the loadout combo popup is open, stops the Timer and clears the pending refresh flag.

`rs/gui/y` is attached directly to the launcher TrayIcon. A click restores the frame to
NORMAL and visible.

`rs/gui/z` is attached directly to the exact Hide/show side panel button and sets the
Client-side toggle signal.

## Withheld nearby classes

- `rs/gui/F`: empty paint-through JPanel with unused image helper field.
- `rs/gui/K`: MouseAdapter whose current exact-v308 enter/exit methods are no-ops.
- `rs/gui/Q`: empty class.

They remain unnamed.

R382 is non-canonical class-only semantic research.
