# Chat 2 — exact-v308 client overlay framework R111

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R111 is a separate non-canonical class-only review for the shared overlay framework used by
the exact-v308 `rs/l/e/a/*` UI/game overlay family.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_2520A829D44C8379CCD5`
- field/method proposals: **0**

## Stable IDs

- `rs/l/e/f` -> `CLIENT_CLASS_000426` -> `ClientOverlay`
- `rs/l/e/f$a` -> `CLIENT_CLASS_000427` -> `OverlayLayer`

## ClientOverlay

The abstract class owns the live overlay registry: concrete overlay singletons, ordered
render lists, an interactive-overlay subset and shared callback maps.

Its runtime dispatch accepts the live Client and one OverlayLayer. It evaluates the
subclass visibility predicate, records active state and invokes the subclass layer-aware
render hook only while active. Client reset/logout paths iterate the same registered
objects through their cleanup hooks.

The ordinary and alternate/resizable client render paths both iterate this family in two
distinct passes:

- LOW;
- HIGH.

That fixes the abstraction as a client overlay component rather than a generic plugin,
scene entity or widget definition.

## OverlayLayer

The enum preserves exactly:

- `LOW`
- `HIGH`

and owns no other state.

Its only meaningful live role is selecting the render pass passed into ClientOverlay.
Concrete overlays frequently return immediately unless the supplied layer equals the one
they own.

## Existing recovered examples

The same framework contains previously reviewed overlays such as R3
`HalloweenHungerGamesOverlay`; R111 does not alter those proposals.

## Naming boundary

No original source class noun survives for the abstract base.

`ClientOverlay` is descriptive exact-behavior recovery at confidence 0.998.
`OverlayLayer` is descriptive but the exact LOW/HIGH constants and exclusive dispatch
role justify confidence 0.999.

## Acceptance boundary

Chat 2 does not promote R111. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_2520A829D44C8379CCD5`.
