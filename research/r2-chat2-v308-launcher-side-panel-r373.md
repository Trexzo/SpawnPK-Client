# Chat 2 — launcher side panel R373

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/J` -> `CLIENT_CLASS_000193` -> `LauncherSidePanel`
- `rs/gui/L` -> `CLIENT_CLASS_000195` -> `LauncherSidePanelTabChangeListener`
- review: `SEMREVIEW_07DB30ADA301EECBCB6E`

## LauncherSidePanel

The panel directly owns the launcher tab surface. Exact labels include:

- `Loadouts`
- `PvP Tracker`
- `GPU (Beta)`
- `Development` when developer mode is enabled
- otherwise `Item Search`

It aggregates the corresponding Swing panels and exposes the tabbed pane/components back to
the launcher.

Most decisively, its placeholder-tab helper contains the exact literal:

`By the way, I'm going to theme this whole side panel.`

That literal plus the launcher-only component composition fixes the semantic role.

## Tab-change listener

`rs/gui/L` is created only by the side panel and installed on its JTabbedPane.

On every change it reads the selected tab index and invokes the active Launcher refresh/update
method. It owns no second role.

## Rejected neighbor

`rs/gui/K` is intentionally withheld. It is a MouseAdapter attached to the side panel, but
its exact-v308 mouseEntered/mouseExited bodies are effectively no-op and do not justify a
meaningful semantic identity.

R373 remains non-canonical semantic research only.
