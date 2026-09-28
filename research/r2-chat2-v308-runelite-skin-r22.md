# Chat 2 — exact-v308 RuneLite look-and-feel semantics R22

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R22 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R21 review batches.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_4A4865C07BEE0FE61F03`
- field/method proposals: **0**

## RuneLite look and feel

- `rs/gui/a` -> `RuneLiteLookAndFeel`
- `rs/gui/b` -> `RuneLiteSkin`

Exact SpawnPK v308 evidence for `RuneLiteLookAndFeel`:

- class extends `org.pushingpixels.substance.api.SubstanceLookAndFeel`;
- its constructor installs one `rs/gui/b` instance as the Substance skin;
- the installed skin's identity is exactly RuneLite.

Exact SpawnPK v308 evidence for `RuneLiteSkin`:

- class extends `org.pushingpixels.substance.api.SubstanceSkin`;
- `getDisplayName()` returns exactly `RuneLite`;
- loads package-relative resource `RuneLite.colorschemes`;
- resolves named schemes including:
  - `RuneLite Active`
  - `RuneLite Enabled`
  - `RuneLite Border`
  - `RuneLite Watermark`
  - `RuneLite Header Border`;
- configures Substance color-scheme bundles, overlay painters, fill/highlight/decoration
  painters, border painters and a square-corner button shaper.

Core R8D independently identified the same raw class, `rs/gui/b`, as a runtime-sensitive
package-relative resource case because of
`Class.getResource("RuneLite.colorschemes")`. R22 consumes that exact evidence without
changing R8D authority.

## Deliberate exclusions

The adjacent raw `rs/gui/b/*` theme data, image/helper and button-shaper classes are not
named by R22. Their roles are visible, but exact semantic identities are weaker than the two
top-level classes and are therefore left unresolved.

## Acceptance boundary

Chat 2 does not promote R22. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to
`SEMREVIEW_4A4865C07BEE0FE61F03`.
