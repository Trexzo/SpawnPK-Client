# Chat 2 — exact-v308 overlay position enum R160

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R160 is a separate non-canonical class-only review for the client overlay placement enum.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_27E3EAA8C4E422D2C546`
- field/method proposals: **0**

## Stable ID

`rs/l/f/l` -> `CLIENT_CLASS_000493` -> `OverlayPosition`

Core's exact baseline ordering assigns this stable ID deterministically from the sorted
exact-v308 `rs/` internal-name set.

## Exact enum values

The enum preserves ten exact constants:

- `DETACHED`
- `DYNAMIC`
- `TOP_LEFT`
- `TOP_CENTER`
- `TOP_RIGHT`
- `BOTTOM_LEFT`
- `BOTTOM_RIGHT`
- `ABOVE_CHATBOX_RIGHT`
- `CANVAS_TOP_RIGHT`
- `TOOLTIP`

## Overlay state ownership

The recovered overlay runtime class `rs/l/f/g` stores this enum directly as overlay
position state.

It:

- defaults a new overlay to `TOP_LEFT`;
- exposes the configured/current position through getters;
- allows the position and runtime override position to be replaced independently.

## Fixed-position geometry

`rs/l/f/c` maintains the overlay-area rectangles and maps the fixed enum values to their
corresponding screen areas.

`rs/l/f/m` consumes the same enum to calculate exact anchor points and placement geometry
inside those rectangles.

The position noun is therefore backed by concrete layout behavior rather than enum strings
alone.

## Renderer behavior

The central overlay renderer/manager `rs/l/f/i` resolves each overlay's effective
`rs/l/f/l` value before drawing.

It distinguishes:

- `DETACHED`
- `DYNAMIC`
- `TOOLTIP`

from fixed anchored positions.

For fixed positions it selects the matching placement rectangle and computes the anchored
point before rendering and stacking overlays.

The same enum participates in drag/drop position selection and runtime position overrides.

## Persistence

The overlay manager reads/writes this exact enum through the overlay settings path.

That makes it the persisted overlay-placement contract, not a one-frame rendering hint.

## Naming boundary

`OverlayPosition` is **0.999**.

The exact enum constants, overlay-owned state fields, layout/renderer consumers and
configuration persistence all independently agree on the semantic role.

## Acceptance boundary

Chat 2 does not promote R160. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_27E3EAA8C4E422D2C546`.
