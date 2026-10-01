# Chat 2 — exact-v308 game client host panel R415

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/E` -> `CLIENT_CLASS_000188` -> `GameClientHostPanel`
- proposal: `SEMPROP_1AF99B2D7EA2D5DAA8CE`
- review: `SEMREVIEW_C2302F80E8DD5C8ABACF`

## Exact role

`rs/gui/E` extends `JPanel` and configures:

- launcher game dimension;
- minimum/preferred size;
- `BorderLayout`;
- black background.

Launcher constructs exactly one instance during window startup.

After the live `Client` is initialized and started, Launcher adds that Client component to
this panel at `BorderLayout.CENTER`, then inserts the panel into the main launcher content
composition.

The class has no other controls or responsibility, fixing its role as the Swing host for the
game client surface.

## Withheld sibling

`rs/gui/F` remains unnamed. It is created by LoadoutsPanel, receives only size/background
configuration, its custom paint method merely delegates to `super.paintComponent`, and its
`GuiImageAsset` field is never assigned or read in exact v308.

R415 remains non-canonical semantic research only.
