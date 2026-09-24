# Chat 2 — exact-v308 combat-info style enums R161

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R161 is a separate non-canonical class-only review for three exact style enums exposed by
the surviving `combatInfo` configuration contract.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_4CAA59E079289FA28AA0`
- field/method proposals: **0**

## Stable IDs

- `rs/s/a/c` -> `CLIENT_CLASS_000857` -> `CombatOverlayStyle`
- `rs/s/a/d` -> `CLIENT_CLASS_000858` -> `HealthBarStyle`
- `rs/s/a/e` -> `CLIENT_CLASS_000859` -> `HitMarkStyle`

## Exact combat-info configuration

The owning config interface preserves the exact group key:

`combatInfo`

Its exact config items include:

- `opponentOverlayStyle` — **Opponent overlay style**
- `bhOverlayStyle` — **Bounty hunter overlay style**
- `bossOverlayStyle` — **Boss overlay style**
- `healthBarStyle` — **Health bars**
- `hitMarkStyle` — **Hitsplats**

These methods return the three enums in this batch directly.

## CombatOverlayStyle

`rs/s/a/c` has exactly:

- `DEFAULT`
- `COMPACT`

The same enum is returned by all three opponent/bounty-hunter/boss overlay-style config
items. A shared name is therefore required; naming it after only one overlay would be too
narrow.

The runtime config manager also compares the selected values against `COMPACT` and updates
live combat-overlay presentation flags.

## HealthBarStyle

`rs/s/a/d` has exactly:

- `OLDSCHOOL`
- `NEWSCHOOL`

The exact config key is `healthBarStyle`, with title `Health bars` and description
`The style of health bar to display`.

Runtime config synchronization compares the value to `NEWSCHOOL` and updates live client
presentation state.

## HitMarkStyle

`rs/s/a/e` has exactly:

- `OLDSCHOOL_WITH_ICONS`
- `OLDSCHOOL`
- `NEWSCHOOL`

The exact config key is `hitMarkStyle`, with title `Hitsplats`.

The runtime manager distinguishes `NEWSCHOOL` and `OLDSCHOOL_WITH_ICONS` when updating
the live hit-mark presentation flags.

## Naming boundary

All three names are **0.999** because the semantic nouns are constrained by surviving config
keys/titles plus exact enum values and runtime consumers.

They remain non-canonical Chat 2 proposals.

## Acceptance boundary

Chat 2 does not promote R161. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_4CAA59E079289FA28AA0`.
