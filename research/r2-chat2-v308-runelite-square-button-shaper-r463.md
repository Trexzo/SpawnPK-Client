# Chat 2 — exact-v308 RuneLite square button shaper R463

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

`rs/gui/c` -> `CLIENT_CLASS_000203` -> `RuneLiteSquareButtonShaper`

- proposal: `SEMPROP_A152ADC720C478E20B72`
- review: `SEMREVIEW_01FD82798886B697CBFF`

## Exact role

R22 already fixes:

- `rs/gui/a` -> RuneLiteLookAndFeel
- `rs/gui/b` -> RuneLiteSkin

RuneLiteSkin constructs exactly one `rs/gui/c` and assigns it to its inherited
`buttonShaper` field.

The helper extends Substance `ClassicButtonShaper` and overrides only:

`getCornerRadius(AbstractButton, float)`

The result is always:

`0.0f`

So the exact behavior is to make RuneLiteSkin buttons square-cornered.

Stable lineage also places the class at `CLIENT_CLASS_000203`, directly between the
already-reviewed RuneLiteLookAndFeel (000202) and RuneLiteSkin (000204).

## Boundary

No broader Substance or layout behavior is claimed. R463 remains non-canonical semantic
research only.
