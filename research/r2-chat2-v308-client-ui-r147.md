# Chat 2 — exact-v308 main client UI and containable frame R147

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R147 resolves the top-level desktop client UI controller and the exact frame sizing /
monitor-containment types it owns.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_5BD02F94F01767ABDBEE`
- field/method proposals: **0**

## Stable IDs

- `rs/gui/u` -> `CLIENT_CLASS_000281` -> `ContainableFrame`
- `rs/gui/u$a` -> `CLIENT_CLASS_000282` -> `FrameContainmentMode`
- `rs/gui/v` -> `CLIENT_CLASS_000283` -> `FrameResizeMode`
- `rs/ui/f` -> `CLIENT_CLASS_001096` -> `ClientUI`

## ClientUI

`rs/ui/f` owns the desktop client UI lifecycle.

Its constructor receives and stores the live:

- `rs/Client`;
- input/client-thread service;
- config manager;
- window-settings config;
- EventBus.

Swing initialization creates the exact `ContainableFrame`, configures title/icon/tray and
window decoration, embeds the running game client, and builds the navigation/sidebar/plugin
panel containers.

Exact persisted UI keys include:

- `runelite`;
- `clientBounds`;
- `clientMaximized`;
- `clientSidebarClosed`.

It handles navigation-button add/remove events and exact sidebar controls:

- `Open SideBar`;
- `Close SideBar`.

When side content is shown/hidden, it calculates the width delta and calls the frame's
width-add/remove methods.

Shutdown posts `ClientShutdown` through EventBus, waits for consumers, and stops the game
client. The class also owns focus/attention/cursor/window behavior.

That complete surface fixes the role as the top-level client UI controller.

## ContainableFrame

`rs/gui/u` extends `JFrame` and is the exact frame created by `ClientUI`.

It owns both sizing enums below.

In `ALWAYS` containment mode, overridden `setLocation` and `setBounds` clamp the
window into the current `GraphicsConfiguration` bounds.

The class also:

- chooses monitor/device geometry;
- adjusts maximized bounds/insets;
- tracks frame edges;
- handles side-content width growth/shrink;
- keeps minimum frame size synchronized with the active layout.

## FrameContainmentMode

`rs/gui/u$a` preserves exact enum constants:

- `ALWAYS`;
- `RESIZING`;
- `NEVER`.

The live window-settings config defaults to `RESIZING`.

`ContainableFrame` uses the enum directly in location/bounds and edge-adjustment behavior.

## FrameResizeMode

`rs/gui/v` preserves exact constants and exact visible labels:

- `KEEP_WINDOW_SIZE` -> `Keep window size`;
- `KEEP_GAME_SIZE` -> `Keep game size`.

`ContainableFrame` branches on this enum when `ClientUI` adds/removes sidebar or plugin
panel width.

`KEEP_WINDOW_SIZE` avoids expanding the frame where possible.
`KEEP_GAME_SIZE` changes frame width with the side-content width so game content remains
the same size.

## Naming boundary

The names describe exact surviving responsibilities and enum semantics. They are not claimed
as recovered original identifiers.

## Acceptance boundary

Chat 2 does not promote R147. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_5BD02F94F01767ABDBEE`.
