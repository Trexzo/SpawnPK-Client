# Chat 2 — exact-v308 raid navigation interface R135

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R135 resolves one class that had remained deliberately blocked in the UI ambiguity triage
because its first-pass evidence could not distinguish a raid tab bar from a reusable raid
header or navigation shell.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_2C4368F6B1F9C2755E43`
- field/method proposals: **0**

## Stable ID

`rs/n/c/d/a` -> `CLIENT_CLASS_000651` -> `RaidNavigationInterface`

## Exact shared-shell construction

The class has one helper that takes an existing interface root and appends the same raid
navigation shell.

That shell contains exact surviving presentation:

- background resource `raids/bg`;
- tab action `Select tab`;
- label `Party`;
- label `Public / Join`;
- label `Invocations`.

The class also loads:

- `raids/tabactive`;
- `raids/tabinactive`;
- `raids/tabdisabled`;
- `raids/sprite 1` through `raids/sprite 4`;
- `raids/owner`.

Its tab-selection method updates those sprites and the Party/Public/Invocations label colors
from one shared selected-tab integer.

## Multi-root proof

Initialization applies that shared shell to multiple distinct raid roots:

- **32300**;
- **32297**;
- **32299**;
- **32298**;
- **32600**.

The resulting containers are not five copies of one content page.

They are populated by separate already-reviewed raid subsystems:

- `rs/n/c/d/c` -> `RaidPartyHubInterface`;
- `rs/n/c/d/b` -> `RaidPartyListInterface`;
- `rs/n/c/d/e` -> `AfflictionTomesInterface`.

The class then finalizes each composed tree.

This is the missing evidence from the earlier ambiguity triage: the class is the shared
navigation shell around several distinct raid surfaces rather than a duplicate party/list/tome
interface.

## Live-state corroboration

R123 ScriptPacket 41 independently targets `rs/n/c/d/a`.

One packet branch updates its boolean navigation state and refreshes the same tab-selection
method. Other ScriptPacket 41 selectors drive the recovered raid hub/list/overlay family.

The class also registers the associated raid overlay consumers at widgets **32317**,
**32465** and **32486** during initialization.

## Naming boundary

`RaidNavigationInterface` is descriptive at **0.999**.

The `Raid` domain is exact from labels/resources and the recovered child surfaces.
`Navigation` is fixed by repeated multi-root shell composition plus live selected-tab state.
`Interface` follows the established R2 class-level convention for this UI-builder family.

The name is not claimed as the original stripped developer identifier.

R135 remains class-only.

## Acceptance boundary

Chat 2 does not promote R135. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_2C4368F6B1F9C2755E43`.
