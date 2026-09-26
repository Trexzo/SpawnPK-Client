# Chat 2 — exact-v308 Control Options attack-settings interface R136

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R136 resolves one class that remained blocked because the first pass could not distinguish
a dedicated subsection builder from a late patch over the reviewed Control Options menu.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_E9153D754ABB6B3C9812`
- field/method proposals: **0**

## Stable ID

`rs/n/c/f` -> `CLIENT_CLASS_000659`
-> `ControlOptionsAttackSettingsInterface`

## Exact child-root identity

The class builds exact root **35112** as a 13-child panel.

Its own exact presentation text is:

- `<u>Player attack options`;
- `<u>NPC/Bot attack options`;
- `<tab=20><img=14> Always right-click clan members`;
- `Select option`.

This is narrower than the R5 `ControlOptionsInterface` / `rs/n/c/ai`, whose exact root
**35000** is titled:

`Control Options Menu`

and includes key bindings, item drag, dropdowns and restore-default behavior in addition to
attack behavior.

## Exact parent/child join

The two builders share the same attack-option dropdown widgets.

The parent `ControlOptionsInterface` builds:

- **35091 / 35096** for player attack behavior;
- **35102 / 35107** for NPC/bot attack behavior.

`rs/n/c/f` then embeds those exact widgets into root **35112** alongside its own
**35113–35116** heading/toggle widgets.

The parent runtime layout code also manipulates those same shared dropdown widgets inside
root 35112, moving/hiding them as the Control Options layout changes.

That resolves the earlier ambiguity: root 35112 is a dedicated Control Options attack/clan
settings child surface, not a second full Control Options interface and not an unrelated
post-build patch.

## Initialization order

The exact interface registry initializes `rs/n/c/ai` first and `rs/n/c/f` later.

That order matches the bytecode relationship: the full parent widget family exists first,
then the narrower child surface composes the already-created attack-option controls.

## Naming boundary

`ControlOptionsAttackSettingsInterface` is descriptive at **0.998**.

`ControlOptions` is inherited from the exact reviewed parent interface.
`AttackSettings` is fixed by the player/NPC attack headings plus clan right-click behavior.
`Interface` follows the established UI-builder convention.

The name is not claimed as the original stripped developer identifier.

R136 remains class-only.

## Acceptance boundary

Chat 2 does not promote R136. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_E9153D754ABB6B3C9812`.
