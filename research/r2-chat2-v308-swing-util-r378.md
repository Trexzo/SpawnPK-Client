# Chat 2 — RuneLite SwingUtil source recovery R378

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/M` -> `CLIENT_CLASS_000197` -> `SwingUtil`
- proposal: `SEMPROP_2E196F5C76B692B8E849`
- review: `SEMREVIEW_FD46994D7D0B64B86052`

## Exact utility surface

The exact-v308 class is stateless Swing infrastructure. Its static methods cover:

- tooltip-manager defaults;
- UIManager color/default setup;
- LookAndFeel installation;
- AbstractButton styling and selected/unselected tooltips;
- icon JButton construction from the already-recovered UI icon model;
- popup-menu item creation;
- system-tray icon construction.

## Source fingerprint

Historical RuneLite/OpenOSRS `net.runelite.client.util.SwingUtil` exposes the same utility
surface.

The exact-v308 implementation also preserves the literal:

`Unable to add system tray icon`

inside the TrayIcon creation failure path, matching the historical source.

## Same-family join

R371 already recovers:

- `rs/gui/N` -> `SwingUtilTrayIconMouseListener`

R378 `rs/gui/M` constructs that exact listener inside its tray-icon helper, closing the
source family cleanly.

## Boundary

This is source-name recovery, not a generic descriptive guess.

R378 remains non-canonical Chat 2 semantic research only.
