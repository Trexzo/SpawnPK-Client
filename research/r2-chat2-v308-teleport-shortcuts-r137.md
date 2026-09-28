# Chat 2 — exact-v308 teleport shortcut interface R137

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R137 resolves one class that was deliberately blocked because its teleport literals and
resource filenames initially appeared to point in different directions.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_C6CFB2BCCB39A2EFAC37`
- field/method proposals: **0**

## Stable ID

`rs/n/c/ak` -> `CLIENT_CLASS_000612` -> `TeleportShortcutInterface`

## Exact root and actions

The class builds exact root **48999**.

Its complete interactive content consists of three teleport actions:

- widget **48997** — `Edgeville teleport`;
- widget **48996** — `Home teleport`;
- widget **48995** — `Bounty teleport`.

The only other user action is the standard:

`Close Window`

control.

There are no destination categories, search state, construction-room names, room-placement
controls or other higher-level content in the class.

## Resource-path ambiguity resolved

The three teleport buttons use sprites from:

`construction/sprite`

and the close control uses:

`LOGS/ICON`

Those are resource paths, not behavior.

The class does not implement construction behavior; the exact click/action strings are all
teleport shortcuts. Exact dependency analysis also finds no project caller other than the
interface-builder registry, so there is no hidden construction owner supplying another role.

The earlier triage therefore overweighted presentation-resource provenance relative to the
complete interactive surface.

## Naming boundary

`TeleportShortcutInterface` is descriptive at **0.998**.

`Teleport` is exact from all three content actions.
`Shortcut` distinguishes the three-button quick-access surface from the broader reviewed
`TeleportSelectionInterface`, which supports generic destination selection.
`Interface` follows the UI-builder convention.

The name is not claimed as the original stripped developer identifier.

R137 remains class-only.

## Triage maintenance

This pass also corrects a stale research-only entry for `rs/n/c/ac` /
`CLIENT_CLASS_000604`: R122 already resolved that class as `ItemListInterface`.
No new proposal is created for that class in R137.

## Acceptance boundary

Chat 2 does not promote R137. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_C6CFB2BCCB39A2EFAC37`.
