# Chat 2 — exact-v308 raid party/theatre overlays R203

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R203 is a separate non-canonical class-only review for two exact-literal raid overlays that
were already consumed by the R123 ScriptPacket 41 analysis but had not themselves received
semantic proposals.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_46A6B9E9F247B81FEF85`
- field/method proposals: **0**

## Stable IDs

- `rs/l/f/a/g/a` -> `CLIENT_CLASS_000464` -> `RaidPartyOverlay`
- `rs/l/f/a/g/c` -> `CLIENT_CLASS_000466` -> `RaidTheatreBar`

Both stable IDs are re-derived from the exact v308 R1 seed ordering.

## RaidPartyOverlay

The constructor writes the exact identity literal:

`RaidPartyOverlay`

The complete rendered surface is one fixed **127x34** raid-party status panel containing:

- `Your points:`;
- the live packet-fed points value;
- `Time:`;
- the live timer value, defaulting to `0:00`.

The class owns the timer start timestamp and, unless the packet freezes explicit time state,
recomputes elapsed time once per second using:

`%d:%02d`

R123 ScriptPacket 41 independently proves the live owner:

- selector 18 initializes/toggles the raid-party timer;
- selector 19 updates points;
- selector 20 updates time.

This is a complete one-domain identity.

## RaidTheatreBar

The constructor writes the exact identity literal:

`RaidTheatreBar`

The class owns one fixed **504x20** overlay surface and records its current clip x/y anchor.

Its sibling `rs/l/f/a/g/b` consumes those exact coordinates to draw the packet-fed theatre
progress bar:

- 500-pixel progress width;
- current/max derived percentage;
- packet-fed text;
- alternate color state.

The sibling renderer has no surviving identity noun of its own, so R203 deliberately does
**not** name it merely by package adjacency.

R123 ScriptPacket 41 constructs/manages this raid overlay family and introduces no unrelated
owner domain.

## Naming boundary

Both names are **0.999** because their identity literals survive exactly in v308 and their
whole-class responsibilities match those literals.

No inferred narrower raid encounter or boss name is introduced.

## Acceptance boundary

Chat 2 does not promote R203. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_46A6B9E9F247B81FEF85`.
