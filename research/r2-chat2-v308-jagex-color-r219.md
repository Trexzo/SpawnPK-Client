# Chat 2 — exact-v308 JagexColor R219

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R219 is a separate non-canonical class-only review for the exact packed Jagex HSL utility.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_800BAAAFD12F32A54DC7`
- field/method proposals: **0**

## Stable ID

- `rs/l/f` -> `CLIENT_CLASS_000440` -> `JagexColor`

## Exact v308 surface

`rs/l/f` is a final utility class with the exact packed Jagex HSL limits:

- hue max: **63**
- saturation max: **7**
- luminance max: **127**

Its short packing is the canonical 6/3/7-bit layout:

- hue in bits 10..15;
- saturation in bits 7..9;
- luminance in bits 0..6.

The exact class provides operations that:

1. pack H/S/L into that representation;
2. unpack hue, saturation and luminance;
3. format a packed value with the exact literal `%02Xh%Xs%02Xl`;
4. convert RGB to packed HSL with brightness/gamma correction and `Color.RGBtoHSB`.

Exact v308 also carries int-returning packing and no-brightness RGB conversion overloads using
the same representation. Those are compatible local extensions rather than evidence for a
different class identity.

## Upstream source-name provenance

RuneLite upstream commit
`b0a10a9c14686f4012eb30865261bbeb3d55af4b` contains
`net.runelite.api.JagexColor` with the same final class, exact 63/7/127 constants, identical
short packing/unpacking, the exact `%02Xh%Xs%02Xl` formatter and the same
`rgbToHSL(int, double)` calculation.

This is stronger than a descriptive-role inference: `JagexColor` is a surviving upstream
source-name provenance match. The confidence remains **0.999**, not 1.0, because the pinned
SpawnPK v308 class contains compatible local overloads beyond the referenced upstream file.

## Duplicate boundary

Before R219, the retained Chat 2 PR patch contains no prior `CLIENT_CLASS_000440` or
`rs/l/f` semantic owner, and the original accepted R2 semantic-seed commits contain no
`JagexColor` / `CLIENT_CLASS_000440` proposal.

## Acceptance boundary

Chat 2 does not promote R219. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_800BAAAFD12F32A54DC7`.
