# Chat 2 — exact-v308 Swing component identifiers R165

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R165 is a separate non-canonical class-only review for a small reusable Swing component
family. Two names survive directly in exact v308; the third is the obfuscated concrete
companion fixed by those exact types.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_75F01B77ACEADD222001`
- field/method proposals: **0**

## Stable IDs

- `rs/ui/components/CustomScrollBarUI`
  -> `CLIENT_CLASS_001036`
  -> `CustomScrollBarUI`
- `rs/ui/components/shadowlabel/JShadowedLabelUI`
  -> `CLIENT_CLASS_001086`
  -> `JShadowedLabelUI`
- `rs/ui/components/shadowlabel/a`
  -> `CLIENT_CLASS_001087`
  -> `JShadowedLabel`

## CustomScrollBarUI

This identifier survives directly in the exact client and is therefore not an inferred
English replacement.

The class extends `BasicScrollBarUI` and:

- paints the scrollbar track with a client palette color;
- paints the thumb with a second palette color;
- removes visible increase/decrease arrow buttons by returning zero-sized buttons;
- exposes the standard `createUI(JComponent)` factory;
- configures the `JScrollBar` unit increment to **16**;
- configures a **7 x 7** preferred scrollbar size.

The surviving identifier and implementation agree exactly.

Confidence: **1.0**.

## JShadowedLabelUI

This identifier also survives directly in the exact client.

The class extends `BasicLabelUI` and overrides enabled-text painting. When the label is
the companion `rs/ui/components/shadowlabel/a`, it:

1. paints the String in the companion's shadow color;
2. offsets that shadow by the companion's configured `Point`;
3. paints the ordinary foreground text at the original coordinates.

Confidence: **1.0**.

## JShadowedLabel

The companion class name is obfuscated, but its responsibility is structurally exact.

It extends `JLabel` and both constructors immediately install:

`new JShadowedLabelUI()`

It owns exactly two shadow-presentation properties:

- shadow `Color`, default `Color.BLACK`;
- shadow `Point`, default `Point(1, 1)`.

Its setters repaint/revalidate the label, and its getters are consumed directly by
`JShadowedLabelUI`.

`JShadowedLabel` is therefore descriptive recovery at **0.999**, not a claim that this
companion's original simple Java identifier survived.

## Naming boundary

R165 deliberately distinguishes exact surviving names from inferred readable names:

- `CustomScrollBarUI`: exact surviving identifier, **1.0**;
- `JShadowedLabelUI`: exact surviving identifier, **1.0**;
- `JShadowedLabel`: behaviorally fixed companion name, **0.999**.

R165 remains class-only.

## Acceptance boundary

Chat 2 does not promote R165. Main/Core may accept any proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_75F01B77ACEADD222001`.
