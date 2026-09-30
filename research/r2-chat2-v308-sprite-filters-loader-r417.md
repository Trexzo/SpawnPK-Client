# Chat 2 — exact-v308 Sprite filters and loader R417

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/G` -> `CLIENT_CLASS_000356` -> `SpriteColorKeyFilter`
- `rs/l/H` -> `CLIENT_CLASS_000357` -> `SpriteRecolorFilter`
- `rs/l/I` -> `CLIENT_CLASS_000358` -> `SpriteLoader`
- review: `SEMREVIEW_9172802146936CCCB5B3`

These classes form the exact contiguous helper layer between R55 `Sprite`
(`CLIENT_CLASS_000355`) and R308 `CombatHudSpriteAssets`
(`CLIENT_CLASS_000359`).

## SpriteColorKeyFilter

Sprite's static `Image + Color` helper constructs this RGBImageFilter and applies it through
FilteredImageSource.

A pixel that exactly matches the configured opaque key color has its alpha byte cleared while
its RGB bytes are preserved. Other pixels are returned unchanged.

## SpriteRecolorFilter

Sprite's `BufferedImage + source Color + replacement Color` helper constructs this filter.

For every pixel it:

1. reads source RGBA from the supplied BufferedImage;
2. checks each source channel against the configured source color with Sprite's tolerance test;
3. shifts matching channels by the source-to-replacement delta;
4. clamps RGB to 0..255;
5. preserves alpha.

## SpriteLoader

The loader owns one static List<Sprite>.

Named sprite registration creates a Sprite, stores its resource path and queues it. The bulk
load path resolves every queued resource with Toolkit/ImageIcon, initializes dimensions,
allocates the pixel buffer, uses PixelGrabber to populate it and performs key-color
normalization for non-exempt sprites.

R308 CombatHudSpriteAssets registers its exact resources through this loader and Client
invokes the loader during live startup.

## Boundary

All three names are descriptive exact-v308 behavioral recoveries. No verbatim stripped
developer class names are claimed.

R417 remains non-canonical semantic research only.
