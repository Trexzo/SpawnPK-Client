# Chat 2 — exact-v308 LoginScreen presentation helpers R158

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R158 is a separate non-canonical class-only review for two presentation helpers exclusively
owned by the recovered `LoginScreen`.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_5257431E8CC3A44230A3`
- field/method proposals: **0**

## Stable IDs

- `rs/l/d/a` -> `CLIENT_CLASS_000391` -> `LoginOrb`
- `rs/l/d/b` -> `CLIENT_CLASS_000392` -> `LoginMessageBox`

## LoginOrb

Only `LoginScreen` references `rs/l/d/a`.

Exact LoginScreen initialization creates a list of **75** instances. It seeds layout with the
exact `orb 1` sprite, then each `LoginOrb` selects from exact `orb N` assets under
`/assets/`.

One instance owns:

- its selected orb sprite;
- current and fixed-point position;
- origin/return position;
- randomized movement mode;
- movement/hover/attraction state.

LoginScreen iterates the same orb list in multiple presentation passes and calls the orb update
with current login-screen interaction coordinates/state. The update computes one of several
movement modes, returns toward its saved origin when appropriate and finally renders the owned
orb sprite at its live position.

No class outside LoginScreen consumes the type.

## LoginMessageBox

Only `LoginScreen` references `rs/l/d/b`.

LoginScreen loads the exact asset:

`/assets/messagebox`

and passes that sprite into each `LoginMessageBox`.

The class stores exactly two message Strings, position, alpha/fade state and presentation mode.
Its renderer draws the messagebox sprite and both text lines, supporting centered or left-side
layout plus fade/reset behavior.

Exact LoginScreen uses include the persistent recovery/PIN guidance:

- `It will be your account's PIN before October 2024`
- `If you do not remember it, request help on our forums!`

LoginScreen also constructs the same class from dynamic two-line login messages.

## Naming boundary

Both names are descriptive rather than claims of lost original identifiers.

- `LoginOrb`: **0.998**
- `LoginMessageBox`: **0.998**

The shared evidence is unusually strong because both types are exclusively LoginScreen-owned,
and their `orb N` / `messagebox` asset identities survive exactly.

## Acceptance boundary

Chat 2 does not promote R158. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_5257431E8CC3A44230A3`.
