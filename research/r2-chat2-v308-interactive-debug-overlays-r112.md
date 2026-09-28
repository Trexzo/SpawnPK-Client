# Chat 2 — exact-v308 interactive/debug overlay semantics R112

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R112 is a separate non-canonical class-only review for the interactive branch of the R111
client overlay framework and two exact diagnostic/editor overlays.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_A8BCFDD6330095C69C77`
- field/method proposals: **0**

## Stable IDs

- `rs/l/e/a` -> `CLIENT_CLASS_000398` -> `InteractiveClientOverlay`
- `rs/l/e/a/e` -> `CLIENT_CLASS_000403` -> `WorldCoordinateOverlay`
- `rs/l/e/a/q` -> `CLIENT_CLASS_000415` -> `InterfaceEditorOverlay`

## InteractiveClientOverlay

This abstract class extends R111 `ClientOverlay` and adds exactly one abstract boolean
interaction hook.

R111 registration detects this subtype and inserts it into a dedicated interactive-overlay
list in addition to the normal render registry.

The live client menu-building path iterates that list. For each active overlay it invokes
the integer interaction hook; if the overlay returns true, ordinary menu construction
returns immediately.

That fixes the subtype as the input/menu-interactive branch of the overlay framework.

## WorldCoordinateOverlay

The HIGH-layer render path calculates world coordinates from:

- local player coordinates;
- client map-base X/Y offsets.

It then derives:

- region X = world X >> 6;
- region Y = world Y >> 6;
- region ID = region X * 256 + region Y.

The exact display text preserves:

- `Coords: @gre@`;
- `Region ID: @whi@`.

Its visibility predicate is a live client setting flag, and its screen position moves around
other active overlays/resizable layout state.

This is a live coordinate/region diagnostic overlay, not dead utility code.

## InterfaceEditorOverlay

The exact client command parser handles:

`edit`

by enabling this singleton and optionally passing an interface child ID to its resolver.

The overlay resolves that child against the currently opened interface hierarchy and stores:

- parent interface ID;
- child index;
- child X offset;
- child Y offset.

Its rendered line preserves:

- X;
- Y;
- `Hovered`;
- child ID;
- `Parent`.

Exact failure diagnostics include:

- `[ERROR] No opened interface to reference!`;
- `[ERROR] Could not find child ID ... in interface ...!`.

While the editor is active, live keyboard handling uses arrow/WASD-style input to mutate
the selected interface child's X/Y arrays directly, marks the interface/client redraw state
and allows the editor to be disabled from keyboard input.

That combination of command activation, widget-tree resolution, live coordinate mutation
and diagnostic display fixes the class as an interface editor overlay rather than merely a
hover inspector.

## Naming boundary

No surviving source nouns were found for these classes.

All three names are therefore descriptive exact-behavior recovery. Confidence remains
0.998 for the framework/coordinate overlay and 0.999 for InterfaceEditorOverlay because its
`edit` command and mutation contract survive directly.

## Acceptance boundary

Chat 2 does not promote R112. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_A8BCFDD6330095C69C77`.
