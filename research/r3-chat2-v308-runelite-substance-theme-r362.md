# Chat 2 R3 — RuneLite Substance theme family R362

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/a` -> `CLIENT_CLASS_000202` -> `RuneLiteLookAndFeel`
- `rs/gui/b` -> `CLIENT_CLASS_000204` -> `RuneLiteSubstanceSkin`
- `rs/gui/c` -> `CLIENT_CLASS_000259` -> `SquareButtonShaper`
- review: `SEMREVIEW_60B40BB14F542F1DC8C5`

The skin identity is explicit rather than inferred: it loads `RuneLite.colorschemes`,
uses many `RuneLite ...` scheme names, and `getDisplayName()` returns `RuneLite`.

`RuneLiteLookAndFeel` is the direct SubstanceLookAndFeel wrapper around that skin.

`SquareButtonShaper` extends ClassicButtonShaper and returns 0.0 for every corner-radius
request.

R362 is descriptive non-canonical semantic research only.
