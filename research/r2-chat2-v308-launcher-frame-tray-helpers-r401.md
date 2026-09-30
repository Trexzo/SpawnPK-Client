# Chat 2 — Launcher frame/tray helpers R401

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/y` -> `CLIENT_CLASS_000286` -> `RestoreLauncherWindowFromTrayMouseHandler`
- `rs/gui/z` -> `CLIENT_CLASS_000287` -> `RequestSidePanelToggleAction`
- `rs/gui/C` -> `CLIENT_CLASS_000186` -> `SetLauncherFrameResizableTask`
- `rs/gui/D` -> `CLIENT_CLASS_000187` -> `ResizeLauncherFrameTask`

Review: `SEMREVIEW_868F1DBBBEE924509E73`

## Tray restore

Launcher creates `rs/gui/y` only as the SpawnPK TrayIcon mouse listener.

Its click behavior sets the launcher JFrame state to NORMAL and makes the frame visible.

## Side-panel toggle request

Launcher creates a small control JButton with exact tooltip:

`Hide/show side panel`

and installs `rs/gui/z`.

The action performs one mutation only:

`Client.i = true`

so the name is deliberately **RequestSidePanelToggleAction**, not an assertion that the
ActionListener itself performs the whole UI transition.

## Frame EDT tasks

`Launcher.b(boolean)` dispatches `rs/gui/C` on SwingUtilities and that task calls only
`JFrame.setResizable(flag)`.

`Launcher.a(int,int,int,int)` dispatches `rs/gui/D`; the task sets the JFrame minimum
size from the first pair and the current size from the second pair.

## Withheld neighbors

- `rs/gui/A` delegates an arbitrary LayoutManager and repositions the launcher top-right
  control strip, but its historical/domain noun is weaker and remains withheld.
- `rs/gui/B` is a stale ActionListener-shaped helper; the live repaint timer uses an
  invokedynamic listener instead.
- `rs/gui/K` is a no-op ClientSidebarPanel MouseAdapter.
- `rs/gui/L` only triggers generic Launcher refresh on tab changes and is not named yet.

R401 remains non-canonical semantic research only.
