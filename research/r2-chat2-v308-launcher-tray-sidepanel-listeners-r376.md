# Chat 2 — launcher tray/side-panel listeners R376

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/y` -> `CLIENT_CLASS_000286` -> `LauncherTrayIconRestoreMouseListener`
- `rs/gui/z` -> `CLIENT_CLASS_000287` -> `LauncherSidePanelToggleActionListener`
- review: `SEMREVIEW_A62DC181EBDBC3D633D2`

## Launcher tray listener

Launcher creates its own TrayIcon, registers `rs/gui/y`, and no other exact-v308 owner
constructs that listener.

On click it:

1. obtains the launcher JFrame;
2. restores it to `Frame.NORMAL`;
3. makes it visible.

This is distinct from R371's SwingUtil-owned tray listener.

## Side-panel toggle listener

Launcher creates a JButton with exact tooltip:

`Hide/show side panel`

and installs `rs/gui/z` as its ActionListener.

The listener's sole action raises the client boolean toggle signal used by the launcher/client
side-panel path.

R376 remains non-canonical semantic research only.
