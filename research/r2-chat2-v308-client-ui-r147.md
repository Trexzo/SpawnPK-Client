# Chat 2 — exact-v308 main client UI and containable frame R147

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R147 resolves the top-level desktop client UI controller and the exact frame sizing /
monitor-containment types it owns.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_4DBAC5B72C88997906D7`
- field/method proposals: **0**

## Stable IDs

- `rs/gui/u` -> `CLIENT_CLASS_000281` -> `ContainableFrame`
- `rs/gui/u$a` -> `CLIENT_CLASS_000282` -> `Mode`
- `rs/gui/v` -> `CLIENT_CLASS_000283` -> `ExpandResizeType`
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

## Mode

`rs/gui/u$a` preserves exact enum constants:

- `ALWAYS`;
- `RESIZING`;
- `NEVER`.

The live window-settings config defaults to `RESIZING`.

`ContainableFrame` uses the enum directly in location/bounds and edge-adjustment behavior.

## ExpandResizeType

`rs/gui/v` preserves exact constants and exact visible labels:

- `KEEP_WINDOW_SIZE` -> `Keep window size`;
- `KEEP_GAME_SIZE` -> `Keep game size`.

`ContainableFrame` branches on this enum when `ClientUI` adds/removes sidebar or plugin
panel width.

`KEEP_WINDOW_SIZE` avoids expanding the frame where possible.
`KEEP_GAME_SIZE` changes frame width with the side-content width so game content remains
the same size.

## Naming boundary

ContainableFrame, its nested Mode enum, ExpandResizeType and ClientUI now all have direct RuneLite source-name provenance. Exact v308 remains runtime authority.

## Acceptance boundary

Chat 2 does not promote R147. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_5BD02F94F01767ABDBEE`.

## Post-R232 source-name correction

Historical/current RuneLite source upgrades two earlier descriptive enum labels without changing R147's proposal count:

- `CLIENT_CLASS_000282` / `rs/gui/u$a`: `FrameContainmentMode` -> `Mode`; old proposal `SEMPROP_9F88494938A142C3C9D8`, corrected `SEMPROP_04999A9E37826EE68154`.
- `CLIENT_CLASS_000283` / `rs/gui/v`: `FrameResizeMode` -> `ExpandResizeType`; old proposal `SEMPROP_EDA45C631DF77328D27E`, corrected `SEMPROP_7212C29EF03DF43A8C5D`.
- old review `SEMREVIEW_5BD02F94F01767ABDBEE` -> corrected review `SEMREVIEW_4DBAC5B72C88997906D7`.
