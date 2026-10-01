# Chat 2 — deferred sprite and RuneLite shaper helpers R392

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/I` -> `CLIENT_CLASS_000358` -> `DeferredSpriteLoader`
- `rs/gui/c` -> `CLIENT_CLASS_000259` -> `RuneLiteZeroRadiusButtonShaper`
- review: `SEMREVIEW_020342D938F581A5936B`

## DeferredSpriteLoader

Registration methods create an empty R55 `Sprite`, store the requested resource path and
append it to a static pending list.

The startup load method later walks that list and:

1. loads `<path>.png` through AWT Toolkit;
2. resolves image width/height with ImageIcon;
3. allocates the Sprite pixel array;
4. copies pixels with PixelGrabber;
5. performs the standard color cleanup for non-alpha resources.

R308 `CombatHudSpriteAssets` registers its Sprite resources through this helper, and
Client invokes the bulk loader during startup.

## RuneLiteZeroRadiusButtonShaper

This class extends Substance `ClassicButtonShaper`, belongs exclusively to R22
`RuneLiteSkin`, and always returns `0.0f` from `getCornerRadius`.

It therefore fixes the RuneLite skin's square/zero-radius button-shaping policy.

R392 remains non-canonical semantic research only.
