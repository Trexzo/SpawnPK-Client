# Chat 2 R3 — launcher side panel R357

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/J` -> `CLIENT_CLASS_000193` -> `LauncherSidePanel`
- `rs/gui/L` -> `CLIENT_CLASS_000195` -> `SidePanelTabChangeListener`
- review: `SEMREVIEW_D48079A6070C39A63B8F`

Launcher owns `rs/gui/J` as its auxiliary tabbed side panel. Exact tabs are:

- Loadouts
- PvP Tracker
- GPU (Beta)
- Development, when developer UI is enabled; otherwise Item Search

The panel owns/exposes those feature components and the JTabbedPane.

`rs/gui/L` is installed directly as the tab pane ChangeListener. On selection changes it
reads the selected index and invokes the launcher refresh/update path.

`rs/gui/K` is intentionally withheld because its current mouse callbacks contain no
meaningful behavior.

R357 is descriptive non-canonical semantic research only.
