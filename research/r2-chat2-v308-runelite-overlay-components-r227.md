# Chat 2 — exact-v308 RuneLite overlay component source recovery R227

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R227 recovers seven real RuneLite overlay-component source classes that remain present in
the exact v308 client.

## Deterministic review result

- candidate classes: **7**
- resolved proposals: **7**
- unresolved: **0**
- review ID: `SEMREVIEW_CBE811E10F4C015AAFE0`
- field/method proposals: **0**

## Stable IDs

- `rs/ui/components/a` -> `CLIENT_CLASS_001037` -> `BackgroundComponent`
- `rs/ui/components/d` -> `CLIENT_CLASS_001066` -> `ComponentConstants`
- `rs/ui/components/e` -> `CLIENT_CLASS_001067` -> `ComponentOrientation`
- `rs/ui/components/q` -> `CLIENT_CLASS_001083` -> `LayoutableRenderableEntity`
- `rs/ui/components/s` -> `CLIENT_CLASS_001085` -> `PanelComponent`
- `rs/ui/components/w` -> `CLIENT_CLASS_001091` -> `RenderableEntity`
- `rs/ui/components/x` -> `CLIENT_CLASS_001092` -> `TextComponent`

## Source provenance

Current RuneLite source at `6e74752caa80fe9cb96cd9b37207e171fa525f07` provides exact source identities for:

- `RenderableEntity`;
- `LayoutableRenderableEntity`;
- `BackgroundComponent`;
- `ComponentConstants`;
- `ComponentOrientation`;
- `PanelComponent`.

The exact bytecode preserves their distinctive interfaces, constants, defaults and render
algorithms.

For `TextComponent`, current RuneLite later inlined its `Point position` into two integer
fields. Historical source at `67496933120316f33bfc480f1a1c67c897cb82b9`, immediately before that change, still has the
exact v308 shape: String text, Point position, Color, outline flag, Font and the identical
embedded-color-tag rendering algorithm.

## Compiler-artifact boundary

R227 does not name the anonymous/listener helper classes emitted around the color picker or
panel implementation. Only classes with a real recovered source identity are proposed.

## Acceptance boundary

Chat 2 does not promote R227. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_CBE811E10F4C015AAFE0`.
