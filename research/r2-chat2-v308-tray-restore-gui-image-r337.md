# Chat 2 continuation — tray restore + GUI image asset R337

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/N` -> `CLIENT_CLASS_000198` -> `TrayIconFrameRestoreMouseAdapter`
- `rs/gui/x` -> `CLIENT_CLASS_000285` -> `GuiImageAsset`
- review: `SEMREVIEW_D496D8951B0148D8D379`

## TrayIcon frame restore

R180 SwingUtil's tray-icon factory constructs `rs/gui/N` with the supplied Frame and adds
it directly as the TrayIcon mouse listener.

On click the adapter restores the Frame to visible/normal state. One exact runtime mode has
an additional hide/reset step before the same restore.

## GUI image asset

`rs/gui/x` is a shared image resource wrapper.

It owns:

- one Image;
- x/y draw coordinates;
- one constructor integer.

It supports both development filesystem loading and packaged class-resource loading, allows
the Image/coordinates to be replaced, and draws through Graphics2D.

Exact consumers include loadout background/prayer/skill/book assets and cached GUI/item
icons, so a feature-specific name would be wrong.

Stable neighbors R280 rs/gui/y and z are 000286 and 000287, fixing this helper at 000285.

R337 remains non-canonical semantic research only.
