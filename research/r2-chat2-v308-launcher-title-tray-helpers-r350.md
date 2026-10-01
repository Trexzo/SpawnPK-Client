# Chat 2 — launcher title/tray GUI helpers R350

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/P` -> `CLIENT_CLASS_000200` -> `TitlePaneControlPanelLayout`
- `rs/gui/N` -> `CLIENT_CLASS_000198` -> `TrayIconRestoreWindowListener`
- review: `SEMREVIEW_E07F22ABF391A0B446AD`

## TitlePaneControlPanelLayout

R344 already established:

- `rs/gui/O` -> `TitlePaneControlPanel`
- `rs/gui/A` -> `TitlePaneControlLayout`

The roles are distinct.

`TitlePaneControlLayout` positions the full control panel inside the launcher title area.
`rs/gui/P` is installed *inside* that panel and lays out its individual child controls.

Its exact dimensions are based on a 23-pixel control height and 27 pixels of preferred width
per child, with the children placed horizontally.

## TrayIconRestoreWindowListener

The GUI utility that creates the system `TrayIcon` installs exactly one
`rs/gui/N` mouse listener.

On a tray click it:

- ensures the captured launcher Frame is visible;
- restores the Frame state to `NORMAL`;
- invokes the exact special refresh/hide path when the current display/platform mode needs it.

The class has no unrelated mouse behavior.

## Boundary

Both names describe exact Swing/AWT roles. R350 remains non-canonical semantic research.
