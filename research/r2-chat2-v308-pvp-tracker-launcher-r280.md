# Chat 2 — exact-v308 PvP tracker updates and launcher controls R280

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

R280 recovers four narrow exact-v308 UI helpers whose roles are fixed by reviewed parents and literal Swing bindings.

- `rs/gui/c/b` -> `CLIENT_CLASS_000261` -> `PvPTrackerMostRecentFightUpdateRunnable`
- `rs/gui/c/c` -> `CLIENT_CLASS_000262` -> `PvPTrackerPreviousFightUpdateRunnable`
- `rs/gui/y` -> `CLIENT_CLASS_000286` -> `RestoreLauncherFromTrayMouseAdapter`
- `rs/gui/z` -> `CLIENT_CLASS_000287` -> `SidePanelToggleAction`
- review: `SEMREVIEW_864C161583CCBDBED781`
- unresolved: **0**
- field/method proposals: **0**

## Exact-v308 evidence

R145 already owns `rs/gui/c/a` as `PvPTrackerSidebarPanel`. Its two public update entry points enqueue `rs/gui/c/b` and `rs/gui/c/c` through `EventQueue.invokeLater`. The first writes the label group beneath **Most Recent 1v1 Fight**; the second writes the mirrored group beneath **Previous 1v1 Fight**. Both preserve the exact death/alive icon and tracker-string formatting behavior.

`Launcher` creates a `TrayIcon` labelled **SpawnPK RSPS** and installs `rs/gui/y` as its mouse listener. Clicking restores the launcher's `JFrame` to state 0 and makes it visible.

The launcher also binds `rs/gui/z` to the button with tooltip **Hide/show side panel**. Its action sets the client side-panel request flag `rs/Client.i` to true.

## Deliberate exclusions

R280 leaves `rs/gui/c` (generic zero-corner button shaper), `rs/gui/c/d` (empty marker), and `rs/gui/x` (generic image helper) unnamed. Already-owned `rs/gui/d..w` are not duplicated.

## Acceptance boundary

R280 is non-canonical research only. These names describe exact-v308 responsibilities; no stripped original source identifiers are claimed and Chat 2 performs no semantic acceptance or rewrite.
