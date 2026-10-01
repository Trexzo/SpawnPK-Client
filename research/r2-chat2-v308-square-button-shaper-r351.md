# Chat 2 — exact-v308 square button shaper R351

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/c` -> `CLIENT_CLASS_000259` -> `SquareButtonShaper`
- proposal: `SEMPROP_A836EA296BAE5083C9C4`
- review: `SEMREVIEW_99DB66E286D93AB15C4C`

The class extends Substance `ClassicButtonShaper`.

The custom launcher Substance skin `rs/gui/b` constructs exactly one instance and assigns
it directly to the inherited `buttonShaper` field.

Its only semantic override is:

`getCornerRadius(AbstractButton,float) -> 0.0f`

So the exact role is a square/zero-corner button shaper.

R351 remains non-canonical semantic research.
