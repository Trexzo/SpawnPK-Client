# Chat 2 — exact-v308 RuneLite Substance look-and-feel family R177

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R177 is a separate non-canonical class-only review for the three-class Swing Substance
look-and-feel family whose exact surviving identity is RuneLite.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_3ABFDCFBEC9729E7A9EE`
- field/method proposals: **0**

## Stable IDs

- `rs/ui/c/a` -> `CLIENT_CLASS_001033` -> `RuneLiteSubstanceSkin`
- `rs/ui/c/b` -> `CLIENT_CLASS_001034` -> `RuneLiteSquareButtonShaper`
- `rs/ui/c/c` -> `CLIENT_CLASS_001035` -> `RuneLiteSubstanceLookAndFeel`

## RuneLiteSubstanceSkin

`rs/ui/c/a` directly extends:

`org.pushingpixels.substance.api.SubstanceSkin`

Its display-name method returns the exact surviving string:

`RuneLite`

The constructor loads the exact skin resource:

`RuneLite.colorschemes`

and resolves/registers a complete named scheme family including:

- `RuneLite Active`
- `RuneLite Border`
- `RuneLite Decorations Separator`
- `RuneLite Decorations Watermark`
- `RuneLite Enabled`
- `RuneLite Header Border`
- `RuneLite Header Watermark`
- `RuneLite Highlight`
- `RuneLite Inner`
- `RuneLite Mark Active`
- `RuneLite Selected Disabled Border`
- `RuneLite Separator`
- `RuneLite Tab Border`
- `RuneLite Watermark`

Those schemes are bound into Substance border, mark, separator, watermark and decoration-area
registrations. This is an exact client skin, not merely a color utility.

## RuneLiteSquareButtonShaper

`rs/ui/c/b` extends:

`org.pushingpixels.substance.api.shaper.ClassicButtonShaper`

It stores the owning `RuneLiteSubstanceSkin` instance and has one behavior override:
`getCornerRadius(AbstractButton, float)` always returns `0.0f`.

That fixes its role as the skin family's square-corner button shaper. The readable name is
descriptive rather than claimed as an original source identifier.

## RuneLiteSubstanceLookAndFeel

`rs/ui/c/c` directly extends:

`org.pushingpixels.substance.api.SubstanceLookAndFeel`

Its constructor does exactly one semantic thing: create `rs/ui/c/a` and pass that
`RuneLiteSubstanceSkin` to the SubstanceLookAndFeel superclass constructor.

The skin and look-and-feel therefore form one exact RuneLite Swing presentation family.

## Naming boundary

The `RuneLite` identity itself survives exactly in the display name and color-scheme
resource. `SubstanceSkin` and `SubstanceLookAndFeel` are exact superclass roles.

`RuneLiteSquareButtonShaper` is descriptive at **0.998** because its original developer
identifier is stripped, but its ownership and zero-corner behavior are exact.

R177 remains class-only and non-canonical.

## Acceptance boundary

Chat 2 does not promote R177. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_3ABFDCFBEC9729E7A9EE`.
