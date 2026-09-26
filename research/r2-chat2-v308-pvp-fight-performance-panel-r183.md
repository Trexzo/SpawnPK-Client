# Chat 2 — exact-v308 PvP Tracker FightPerformancePanel source recovery R183

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

External source corroboration:

`open-osrs/OpenOSRS-RL-hub@32df35dcf71dde2f9f5e81ce8170bd2da325b63c pvpperformancetracker/src/main/java/matsyir/pvpperformancetracker/FightPerformancePanel.java`

R183 is a separate non-canonical class-only review for the per-fight Swing presentation
inside the reviewed PvP Tracker panel.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_A3664323BAFEE620DA1D`
- field/method proposals: **0**

## Stable ID

`rs/s/q/b/a` -> `CLIENT_CLASS_000954` -> `FightPerformancePanel`

## Exact v308 structure

The class:

- directly extends `JPanel`;
- stores one `rs/s/q/a/a` fight model;
- owns paired fighter panels and labels;
- preserves static normal/hover borders;
- exposes constructor/update/get/set fight behavior.

Its exact presentation fingerprint includes:

`HH:mm:ss 'on' yyyy/MM/dd`

and the resources:

- `ico_skull.png`;
- `ico_user.png`;
- `ico_pray.png`;
- `ico_magic.png`;
- `ico_damage.png`.

The parent is the reviewed `PvPTrackerPanel`, and the consumed fight object is R142's
reviewed `PvPTrackerFight`.

## Original source-name recovery

The pinned OpenOSRS PvP Performance Tracker source defines:

`FightPerformancePanel`

with the same:

- JPanel responsibility;
- one fight model;
- exact date formatter;
- normal/hover border concept;
- paired fighter-performance presentation;
- damage/magic/prayer/death information surface.

This makes the class-name recovery substantially stronger than a descriptive guess.

## Deliberate model boundary

The upstream source's adjacent model is named `FightPerformance`, but SpawnPK's exact-v308
model is structurally simplified relative to that source revision.

R183 therefore recovers only the panel's source name. It does **not** rewrite the established
R142 model semantics merely because the upstream type has a related name.

## Provenance boundary

`FightPerformancePanel` is **0.999**.

External source supplies original-name provenance. The pinned v308 JAR remains authoritative
for runtime identity and behavior.

R183 remains class-only and non-canonical.

## Acceptance boundary

Chat 2 does not promote R183. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_A3664323BAFEE620DA1D`.
