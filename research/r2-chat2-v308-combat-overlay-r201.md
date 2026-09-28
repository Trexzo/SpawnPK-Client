# Chat 2 — exact-v308 CombatOverlay R201

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R201 is a separate non-canonical class-only review for the client-native combat-status
overlay.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_997D257B6FB8A522CED6`
- field/method proposals: **0**

## Stable ID

`rs/l/f/a/c/d`
-> `CLIENT_CLASS_000453`
-> `CombatOverlay`

## Exact surviving identity

The constructor calls the shared overlay identity setter with the exact literal:

`CombatOverlay`

This fixes the readable noun directly.

The class is distinct from the separately reviewed RuneLite-style
`CombatOverlaysPlugin`, `CombatOverlayConfig` and `CombatOverlayStyle` classes. R201
covers the client-native live overlay object.

## Overlay contract

The class extends the shared positioned-overlay base and configures:

- overlay position/layer state;
- a 10-pixel presentation parameter;
- exact bounds/inset state.

Its renderer returns an empty dimension whenever the combat overlay is not currently
eligible to display.

## Target resolution

The live state includes:

- target name;
- maximum combat/health value;
- current combat/health value;
- animated displayed value;
- target entity index;
- last-update timestamp.

The entity index is resolved against the client NPC/player arrays. The resolved entity name
must match the stored target name before its live value is consumed.

That prevents the display from silently following a recycled entity slot.

## Health/progress presentation

The renderer derives the bar width from current / maximum state and maintains a separate
animated display value for recent combat loss.

It renders:

- the target name;
- the current/max combat values;
- the proportional progress/health bar;
- the animated recent-loss portion.

Compact/default drawing branches still consume the same combat state and do not introduce a
second subsystem responsibility.

## Visibility lifecycle

The overlay requires:

- non-null target name;
- positive maximum value;
- a recent update timestamp.

It expires after **20 seconds** and is additionally suppressed by exact client/interface
visibility conditions.

## Naming boundary

`CombatOverlay` is **0.999**.

The exact identity literal survives in v308, and the whole class is one combat target/status
overlay lifecycle. No inferred narrower noun such as boss/opponent/player overlay is imposed.

## Acceptance boundary

Chat 2 does not promote R201. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_997D257B6FB8A522CED6`.
