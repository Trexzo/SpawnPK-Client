# Chat 2 — RuneLite skin button shaper R377

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/c` -> `CLIENT_CLASS_000259` -> `RuneLiteSkinButtonShaper`
- proposal: `SEMPROP_54CDF920BE8A8E19F552`
- review: `SEMREVIEW_95F9CD7EF2B2706AFBC4`

## Exact behavior

The class extends `ClassicButtonShaper`.

Its only meaningful override is:

`getCornerRadius(AbstractButton, float) -> 0.0f`

so all buttons shaped through this helper use square corners.

## Ownership

R22 already fixes `rs/gui/b` as `RuneLiteSkin`.

That skin is the exact-v308 constructor/consumer of `rs/gui/c`, fixing this helper inside
the older RuneLite skin family.

## Naming boundary

R177 separately owns `rs/ui/c/b` as `RuneLiteSquareButtonShaper`.

R377 deliberately uses the distinct name `RuneLiteSkinButtonShaper` so the two different
raw classes/families do not collapse into one semantic identity.

No original standalone source identifier for this helper is claimed.

R377 remains non-canonical semantic research only.
