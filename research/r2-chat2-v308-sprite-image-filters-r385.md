# Chat 2 — Sprite image filters R385

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/G` -> `CLIENT_CLASS_000356` -> `ColorKeyTransparencyFilter`
- `rs/l/H` -> `CLIENT_CLASS_000357` -> `SpriteRecolorFilter`
- review: `SEMREVIEW_AE3D0DC34208886BD1F7`

## Color-key transparency

R55 already fixes `rs/l/F` as `Sprite`.

`rs/l/G` extends `RGBImageFilter`, stores one Color and its opaque RGB value, and changes
only pixels matching that key. A matching pixel is returned without an alpha byte; all
others pass through unchanged.

Sprite's static `Image + Color` transform helper constructs exactly this filter and returns
the resulting FilteredImageSource as an AWT Image.

## Sprite recolor

`rs/l/H` also extends `RGBImageFilter`.

It stores:

- a reference BufferedImage;
- source Color;
- target Color.

For each coordinate it reads the reference pixel, checks its channels against the source
Color using Sprite's exact tolerance helper, and when matched shifts the channels by the
source-to-target delta. Alpha is retained and resulting channels are clamped to 0..255.

Sprite's static `BufferedImage + source Color + target Color` helper is the sole owner of
this filter.

## Boundary

Both names are exact-behavior descriptions of private Sprite image-transform helpers. They
do not claim lost original developer identifiers.

R385 remains non-canonical class-only semantic research.
