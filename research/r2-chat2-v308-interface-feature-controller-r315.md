# Chat 2 — exact-v308 interface feature controller R315

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/l/e/f` -> `CLIENT_CLASS_000426` -> `InterfaceFeatureController`
- proposal: `SEMPROP_7A4D80D7D24473E2E452`
- review: `SEMREVIEW_2D36D0645A1C80DB8364`
- unresolved: **0**
- member proposals: **0**

## Exact renderer relationship

R302 fixed the central widget traversal owner as `InterfaceRenderer`.

R314 then fixed `rs/l/e/i` as `InterfaceWidgetRenderCallback`. During live widget
traversal, `InterfaceRenderer` iterates active `rs/l/e/f` instances, queries each one by
the current `RSInterface.aw` widget id, and invokes the returned callback with the
concrete RSInterface and already-resolved screen x/y coordinates.

That makes `rs/l/e/f` part of the live interface render-control path, not an unrelated
container inferred from package adjacency.

## Callback registry ownership

Each `rs/l/e/f` instance owns the int-keyed callback registry consumed by that renderer
path.

Its protected registration helpers bind either:

- one widget id; or
- an array of widget ids

to a shared `InterfaceWidgetRenderCallback`.

Only controllers whose callback registry is non-empty enter the renderer-consumed active
controller list.

The controller therefore owns both feature-specific widget callback registration and the
runtime lookup surface used by `InterfaceRenderer`.

## Concrete feature family

The exact-v308 recovered-source inventory independently places `rs/l/e/f` with the
concrete `rs/l/e/a/*` controller family and records imports of the concrete controller
implementations plus `GamblingInterface`.

This corroborates the feature-controller role exposed directly by the renderer/callback
contract without requiring a guessed gameplay-domain noun.

## Naming boundary

`InterfaceFeatureController` is intentionally descriptive.

The exact role is strong, but no surviving original source identifier proves a narrower
historical class noun. The name therefore captures the shared interface-feature control
contract and does not claim original-source identity.

Confidence is **0.998**.

## Acceptance boundary

R315 is non-canonical semantic research only. Chat 2 performs no acceptance or source
rewrite.
