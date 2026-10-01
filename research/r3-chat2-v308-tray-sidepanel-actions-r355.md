# Chat 2 R3 — tray restore / side-panel toggle actions R355

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/y` -> `CLIENT_CLASS_000286` -> `TrayWindowRestoreMouseListener`
- `rs/gui/z` -> `CLIENT_CLASS_000287` -> `SidePanelToggleAction`
- review: `SEMREVIEW_B6304426699FC8B88C1D`

### Tray restore

Launcher installs `rs/gui/y` directly on the SpawnPK TrayIcon. On click, the listener:

1. obtains the active Launcher JFrame;
2. sets frame state to NORMAL;
3. sets the frame visible.

### Side-panel toggle

Launcher creates the title-bar button with tooltip `Hide/show side panel` and installs
`rs/gui/z`. Its action performs one mutation: `Client.i = true`, the toggle-request flag
for that exact button path.

The nearby `rs/gui/B` helper is not retained because no executable exact-v308 construction
site was found.

R355 is descriptive non-canonical semantic research only.
