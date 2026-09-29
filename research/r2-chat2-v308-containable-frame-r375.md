# Chat 2 — RuneLite ContainableFrame family R375

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/u` -> `CLIENT_CLASS_000281` -> `ContainableFrame`
- `rs/gui/u$a` -> `CLIENT_CLASS_000282` -> `ContainableFrameMode`
- `rs/gui/v` -> `CLIENT_CLASS_000283` -> `ExpandResizeType`
- review: `SEMREVIEW_5D249D59E0FB3FA60434`

## Source match

Historical RuneLite/OpenOSRS source contains `net.runelite.client.ui.ContainableFrame` with:

- JFrame base class;
- a fixed 40px screen-edge threshold;
- location/bounds clamping to screen geometry;
- containment modes;
- ExpandResizeType handling.

Exact v308 reproduces that structure.

## Nested frame mode

The nested exact-v308 enum preserves:

- `ALWAYS`
- `RESIZING`
- `NEVER`

Historical source exposes exactly those constants as `ContainableFrame.Mode`. The review
uses `ContainableFrameMode` because semantic names are global Java identifiers rather than
nested-source syntax.

## ExpandResizeType

The exact enum preserves:

- `KEEP_WINDOW_SIZE("Keep window size")`
- `KEEP_GAME_SIZE("Keep game size")`

That is an exact source-name and constant/display-string match for RuneLite
`ExpandResizeType`.

## Already-owned neighbor

`rs/gui/w` is not part of R375 because R234 already recovers it as source-proven
`FontManager`.

R375 remains non-canonical semantic research only.
