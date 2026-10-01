# Chat 2 successor — exact-v308 font markup and Sprite filter R379

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/i` -> `CLIENT_CLASS_000498` -> `PingPongValue`
- `rs/l/k` -> `CLIENT_CLASS_000500` -> `RSFontMarkupParser`
- `rs/l/G` -> `CLIENT_CLASS_000356` -> `ColorKeyTransparencyFilter`
- review: `SEMREVIEW_97DED3846D4D5F72774B`

## PingPongValue

The class stores:

- a final upper bound;
- a current integer initialized to 0;
- a direction initialized to +1.

Every update adds the direction to the current value. At the upper bound direction changes to
-1; at the lower bound it changes back to +1.

RSFontMarkupParser constructs four exact instances with maxima:

- 25
- 50
- 125
- 250

Client advances all four together from its live render/update path.

## RSFontMarkupParser

Exact reverse references are limited to:

- Client;
- R55 `RSFont`;
- the class itself.

The class contains fourteen static recognizers taking `String,start,end` and returning
integer parse/control values.

R55 RSFont delegates into these methods throughout both rendering and width/measurement
logic. Parsed results drive formatting state, Sprite/icon insertion, offsets and color/effect
state. The parser also recognizes animated/pulsing forms such as `pu1` and `pu2`, whose
colors depend on the PingPongValue instances above.

The name is deliberately scoped to RSFont markup, not a generic text parser.

## ColorKeyTransparencyFilter

`rs/l/G` extends AWT `RGBImageFilter`.

Construction stores one Color and its opaque ARGB key. For each pixel:

- compare the pixel with alpha forced opaque against the stored key;
- if equal, clear the alpha byte while preserving RGB;
- otherwise return the original pixel unchanged.

R55 Sprite is its only external exact-v308 owner. Sprite wraps it in
`FilteredImageSource` and builds the resulting AWT Image through `Toolkit`.

## Boundary

All names are descriptive exact-v308 roles only. No original stripped developer identifiers
are claimed. R379 remains non-canonical semantic research.
