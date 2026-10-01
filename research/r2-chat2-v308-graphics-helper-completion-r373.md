# Chat 2 — exact-v308 graphics helper completion R373

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/D` -> `CLIENT_CLASS_000353` -> `InitialLauncherWindowLayoutTask`
- `rs/l/G` -> `CLIENT_CLASS_000356` -> `ColorKeyTransparencyFilter`
- `rs/l/H` -> `CLIENT_CLASS_000357` -> `SpriteColorRangeReplacementFilter`
- `rs/l/I` -> `CLIENT_CLASS_000358` -> `DeferredSpriteLoader`
- review: `SEMREVIEW_29093310EAE4B9BB47B5`

## InitialLauncherWindowLayoutTask

R85 already fixes `rs/l/C` as `DepthBufferedImageSurface`.

On the first surface draw, that class schedules `rs/l/D` on the Swing EDT and flips a
static one-shot guard.

The task sizes the Launcher window to one of two exact client layouts:

- 1134x537
- 1312x800

It centers the frame on screen and conditionally maximizes the larger layout when screen
width is insufficient.

## Sprite filters

R55 already fixes `rs/l/F` as `Sprite`.

`rs/l/G` is used only by `Sprite.a(Image, Color)`. It performs exact color-key
transparency by stripping alpha when an input pixel matches the configured key color.

`rs/l/H` is used only by `Sprite.a(BufferedImage, Color, Color)`. It performs a
tolerance-based RGB range match against the first color and shifts matching channels toward
the replacement color while preserving alpha.

## DeferredSpriteLoader

`rs/l/I` owns one private pending Sprite list.

Its registration methods create empty Sprite objects, attach asset paths and queue them.
Its batch-load method later resolves Toolkit images, dimensions and pixel arrays, then
applies normal Sprite color-key cleanup.

Client invokes that batch materialization during startup after the static HUD-sprite
registries have declared their deferred assets.

## Withheld direct-core neighbors

`rs/l/L` remains under review as a Sprite-style color transform utility.

`rs/l/M` remains under review as a broad software raster primitive layer; its exact
relationship to the already-recovered lower raster base must be fixed before naming.

R373 is non-canonical semantic research only.
