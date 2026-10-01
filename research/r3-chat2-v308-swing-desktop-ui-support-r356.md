# Chat 2 R3 — shared Swing/desktop UI support R356

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/M` -> `CLIENT_CLASS_000197` -> `SwingDesktopUiSupport`
- `rs/gui/N` -> `CLIENT_CLASS_000198` -> `TrayIconFrameRestoreListener`
- review: `SEMREVIEW_69107BB46A119175BB1D`

`SwingDesktopUiSupport` centralizes Swing tooltip/UIManager defaults, LookAndFeel
installation, global font propagation, flat/icon button helpers and system-tray creation.

Its tray helper installs `TrayIconFrameRestoreListener`, which restores the supplied Frame
to visible/NORMAL state on tray-icon click, including the existing platform-specific focus
workaround.

R356 is descriptive non-canonical semantic research only.
