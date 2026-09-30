# Chat 2 — positioned UI image R383

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

`rs/gui/x` -> `CLIENT_CLASS_000285` -> `PositionedUiImage`

Proposal: `SEMPROP_C6914C85109D6A28CD13`

Review: `SEMREVIEW_7D9DBA7A441C1DF416B2`

## Exact behavior

The class owns:

- one `java.awt.Image`;
- mutable x/y coordinates;
- one constructor-supplied auxiliary integer whose narrower meaning does not survive strongly enough to name.

Its String loader resolves client resources in two exact branches:

- file-backed resource URLs -> Toolkit image loading;
- packaged/classpath resources -> ImageIO.

The loaded image is retained and success is reported from whether the image exists.

The positioning method updates x/y.

The Graphics method creates a Graphics2D and draws the stored image at exactly x/y when the
live Launcher surface is available.

## Exact consumers

Reverse references are confined to launcher/loadout presentation classes, including:

- `rs/gui/b/b/b`
- `rs/gui/b/e`
- `rs/gui/b/f`
- `rs/gui/b/g`
- `rs/gui/b/c/b`
- `rs/gui/b/c/c`
- the intentionally unnamed `rs/gui/F`

No gameplay/world subsystem owns the type.

## Boundary

The name remains deliberately generic: `PositionedUiImage`.

Exact v308 proves reusable UI image loading, storage, positioning and drawing but does not
prove a narrower historical noun such as sprite/icon/badge.

R383 remains non-canonical class-only semantic research.
