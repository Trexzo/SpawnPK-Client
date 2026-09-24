# Chat 2 — exact-v308 PvP Tracker fight models R142

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R142 resolves the two internal data-model classes connecting the R141 in-game PvP Tracker
packet/overlay layer to the R12 PvP Tracker plugin, panel and fight history.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_777E2500491C487C174F`
- field/method proposals: **0**

## Stable IDs

- `rs/s/q/a/a` -> `CLIENT_CLASS_000951` -> `PvPTrackerFight`
- `rs/s/q/a/b` -> `CLIENT_CLASS_000952` -> `PvPTrackerFighterStats`

## PvPTrackerFight

A new fight contains exactly two `rs/s/q/a/b` participant records.

Both start with exact name sentinel:

`N/A`

The fight also owns one aggregate integer and compares the two participant records through
their two percentage metrics.

R12 `PvPTrackerPlugin` owns:

- one current `rs/s/q/a/a`;
- one `ArrayList<rs/s/q/a/a>` fight history;
- the reviewed `PvPTrackerPanel`.

When a current fight becomes complete, the plugin creates a new fight object, deep-copies
both fighter records into it, copies the fight aggregate, appends that snapshot to history,
sends the archived fight to the panel, then replaces current state with a fresh fight.

That current-to-history lifecycle fixes `Fight` independently of obfuscated package names.

## PvPTrackerFighterStats

Each fighter record owns:

- one name;
- five integer state values;
- one boolean state.

Exact methods:

- increment one current/total pair and conditionally increment its successful/current count;
- increment a second current/total pair in the same way;
- directly set either pair;
- accumulate one integer aggregate;
- compute two clamped ratios;
- format each pair as current / total / percentage;
- expose the aggregate;
- expose the boolean state;
- expose/set the fighter name.

R141 `PvPTrackerPacketHandler` writes these records through the exact R12 tracker model.

When a fight is archived, `PvPTrackerPlugin` copies each fighter's:

- name;
- aggregate value;
- both paired counter sets;
- boolean death/status flag.

The record therefore represents fighter-specific tracker statistics rather than a generic
player object.

## Naming boundary

Both names are **0.999**.

`PvPTracker` is exact from the already-reviewed plugin graph.
`Fight` is fixed by current/history ownership and archive lifecycle.
`FighterStats` is descriptive of the per-participant name/counter/ratio/death record and
does not claim narrower original field semantics.

R142 remains class-only.

## Acceptance boundary

Chat 2 does not promote R142. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_777E2500491C487C174F`.
