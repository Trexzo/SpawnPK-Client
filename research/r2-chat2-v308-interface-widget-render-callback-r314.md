# Chat 2 — exact-v308 interface widget render callback R314

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/l/e/i` -> `CLIENT_CLASS_000430` -> `InterfaceWidgetRenderCallback`
- proposal: `SEMPROP_38DDB6ADCD985A7A7B08`
- review: `SEMREVIEW_F43BBFA23C22B1651899`
- unresolved: **0**
- member proposals: **0**

## Exact renderer dispatch

The older frontier audit proved only the raw callback signature
`void a(rs.n.e, int, int)` and correctly withheld a noun.

R302 subsequently fixed the live caller as `InterfaceRenderer`. During exact widget
traversal the renderer iterates active `rs/l/e/f` feature controllers, looks up a callback
by the current `RSInterface.aw` id, and invokes the callback with the concrete RSInterface
plus the widget's already-resolved screen x/y coordinates.

## Exact registration contract

Each `rs/l/e/f` controller owns an int-keyed map of `rs/l/e/i` callbacks.

Its protected registration helpers bind either one widget id or an array of widget ids to a
callback. Controllers with non-empty callback maps are placed in the exact list consumed by
`InterfaceRenderer`.

Concrete `rs/l/e/a/*` controllers create these callbacks for feature-specific widget-id
sets. Implementations inspect the supplied RSInterface and perform presentation work,
including sprite drawing from widget state.

## Distinction from R288

R314 does not duplicate R288 `InterfaceDrawCallback`.

R288's callback is stored directly on RSInterface, preserves `draw(int,int)`, and is
invoked through widget-owned draw phases.

R314's callback is stored externally in active feature-controller registries, is keyed by
widget id, receives the concrete RSInterface object, and is dynamically dispatched by the
central InterfaceRenderer.

`InterfaceWidgetRenderCallback` therefore captures the exact contract without claiming a
lost original source identifier.

Confidence is **0.998**.

## Acceptance boundary

R314 is non-canonical semantic research only. Chat 2 performs no acceptance or source rewrite.
