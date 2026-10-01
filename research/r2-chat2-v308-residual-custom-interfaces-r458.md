# Chat 2 — residual custom-interface identities R458

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/A` -> `CLIENT_CLASS_000546` -> `ConfirmationDialogInterface`
- `rs/n/c/D` -> `CLIENT_CLASS_000549` -> `DuelLoadLastRulesPatch`
- `rs/n/c/I` -> `CLIENT_CLASS_000554` -> `EquipmentTabEnhancementPatch`
- `rs/n/c/f` -> `CLIENT_CLASS_000659` -> `AttackOptionsInterfacePatch`
- `rs/n/c/r` -> `CLIENT_CLASS_000671` -> `ClanWarAcceptInterface`

Review: `SEMREVIEW_23698100740299035943`

## Confirmation dialog

`rs/n/c/A` owns root 14170 and exact generic confirmation content:

- `Please confirm your choice.`
- `Confirm`
- `Cancel`
- `<img=25> Close window`

Its helpers alter/reset the same confirmation surface for alternate layouts. No narrower
domain is encoded in the class.

## Duel load-last patch

`rs/n/c/D` does not create an independent interface root. It reads root 6575's current
child arrays, appends two children and writes the expanded arrays back.

Exact content:

- `misc/duel load`
- `Load last rules`
- `Load last duel`

The semantic name therefore uses **Patch**.

## Equipment-tab enhancement

`rs/n/c/I` mutates existing equipment-tab presentation and adds the controls:

- `Show Equipment Stats`
- `Show Items Kept on Death`
- `Remove`

Independent exact-client research already confirms the native equipment Stats and Items
Kept on Death actions.

## Attack-options patch

`rs/n/c/f` patches root 35112 with:

- `Player attack options`
- `NPC/Bot attack options`
- `Always right-click clan members`

It is also referenced from the live client render/control path outside the central registry.

## Clan-war accept interface

`rs/n/c/r` builds root 34000 with a clan-themed acceptance panel and exact `Accept`
action. Independent exact-current research separates this acceptance surface from the
configurable Clan Wars setup interface.

## Boundary

These are descriptive exact-v308 names only. R458 remains non-canonical Chat 2 research.
