# Chat 2 — exact-v308 PvP Tracker overlay / ScriptPacket 8 R141

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R141 resolves the previously withheld ScriptPacket 8 family by joining its in-game overlay
and packet flow to the already-reviewed exact PvP Tracker plugin graph from R12.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_14F944AD06349D26BCA6`
- field/method proposals: **0**

## Stable IDs

- `rs/l/e/a/c` -> `CLIENT_CLASS_000401` -> `PvPTrackerOverlay`
- `rs/l/e/a/d` -> `CLIENT_CLASS_000402` -> `PvPTrackerPacketHandler`

## Independent exact PvP Tracker authority

R12 already resolves the external tracker graph:

- `rs/s/q/a` -> `PvPTrackerConfig`;
- `rs/s/q/b` -> `PvPTrackerPanel`;
- `rs/s/q/d` -> `PvPTrackerPlugin`.

That evidence includes:

- exact plugin title `PvP Tracker`;
- exact config key `pvptracker`;
- `Current Fight`;
- `Fight History (Filter by Usernames):`;
- `Filter Usernames:`;
- `pvp_icon.png`;
- tracker icons for user, damage, magic, prayer and skull state.

ScriptPacket 8 directly updates that exact plugin/model graph.

## In-game overlay

The overlay preserves exact fight-stat presentation including:

- `Correct F3:`;
- `Magic:`;
- `Damage:`;
- `N/A`;
- `0 / 0`;
- `0/0 (0%)`;
- `[0%]`.

It renders two paired fighter panels from separate names, counters, ratios, differences and
status strings.

That paired state is synchronized into the R12 PvP Tracker current-fight model and panel.

## ScriptPacket 8

R115 registers singleton `rs/l/e/a/c.v` as exact ScriptPacket **8**.
The exact static initializer constructs `rs/l/e/a/d` into that field.

The handler has selectors **1–8**.

Across the full selector surface it updates:

- tracker/overlay presentation flags;
- both fighter names/status values;
- paired current/total counters and percentages;
- paired stat differences;
- colored correction/F3 values;
- death/status state.

For tracker-model updates it reaches the exact `PvPTrackerPlugin` singleton at
`rs/s/q/d.e`, mutates its current-fight model, and refreshes the `PvPTrackerPanel`.
Several refreshes are marshalled through `SwingUtilities.invokeLater`.

The exact `@red@` + `Died` handling marks the corresponding fighter as dead in the same
tracker model.

No selector establishes a second unrelated feature domain.

## Naming boundary

Both names are **0.999**.

The PvP Tracker noun is exact from R12, and R141 proves the in-game overlay/packet layer is
part of that same graph.

R141 remains class-only.

## Residual ScriptPacket boundary

After R141, only two ScriptPacket IDs remain deliberately unnamed:

- **27** — twelve-string overlay with no self-identifying content domain;
- **32** — mixed handler with no honest single subsystem noun.

## Acceptance boundary

Chat 2 does not promote R141. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_14F944AD06349D26BCA6`.
