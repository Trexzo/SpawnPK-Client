# Chat 2 — exact-v308 curve extrapolation mode semantics R45

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R45 is a separate non-canonical class-only semantic review batch following R44's
Keyframe / AnimationCurve recovery.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_EE654F9AE8DD697568DB`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/u/i` -> `CLIENT_CLASS_001014`

## `rs/u/i` -> `CurveExtrapolationMode`

R44 `AnimationCurve` decodes two values of this exact type before its Keyframe array.
They are stored separately and consumed only at the two curve boundaries:

- one mode when the requested time lies before the first keyframe;
- one mode when the requested time lies after the last keyframe.

The out-of-range evaluator branches on the five enum-like instances to select endpoint
hold or alternative repeated/cyclic, offset, and reflected/ping-pong style remapping
before evaluating the curve again.

The type itself is a five-instance encoded value set with no unrelated payload or consumer
role. That fixes the semantic family as curve extrapolation / pre-post behavior.

The conservative semantic name is therefore `CurveExtrapolationMode`.

## Deliberately withheld adjacent enums

R45 does not name `rs/u/c` or `rs/u/e`. They are clearly keyframe-animation channel /
property selectors, but the exact noun split between transform target type, channel type
and component/property type is not yet sufficiently unique to justify a proposal.

## Naming boundary

This is a semantic recovery name, not a claim of a verbatim original SpawnPK identifier.

## Acceptance boundary

Chat 2 does not promote R45. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_EE654F9AE8DD697568DB`.
