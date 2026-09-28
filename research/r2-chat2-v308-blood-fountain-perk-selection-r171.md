# Chat 2 — exact-v308 Blood Fountain perk selection R171

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R171 is a separate non-canonical class-only review for the live Blood Fountain perk
selection presentation layered over the already-reviewed Blood Fountain perk tree interface.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_C2229E2B5CBEFAA12B55`
- field/method proposals: **0**

## Stable IDs

- `rs/l/c/e` -> `CLIENT_CLASS_000388` -> `BloodFountainPerkEntry`
- `rs/l/c/f` -> `CLIENT_CLASS_000389` -> `BloodFountainPerkSelectionOverlay`

## Existing interface authority

R2 already resolves `rs/n/c/aD` as `BloodFountainPerkTreeInterface`.

Its exact v308 presentation includes the title:

`<img=186> Blood Fountain Perk Tree <img=186>`

and exact perk-tree state such as:

`Selected perk: Blood vengeance`

R171 does not rename that static interface builder. It recovers the two untouched runtime
classes that implement its interactive perk-node presentation.

## BloodFountainPerkEntry

`rs/l/c/e` is a compact four-field record:

- one perk-label String;
- x coordinate;
- y coordinate;
- one integer presentation state.

The constructor fixes the label/coordinates and initializes state to zero. The owning
overlay reads the label for hover text, the coordinates for node placement and the state
as the selector for the three live perk sprites.

This is not a generic coordinate record in practice: the exact consumer fills it exclusively
with Blood Fountain perk names.

## BloodFountainPerkSelectionOverlay

`rs/l/c/f` extends the client-side overlay base.

Its renderer immediately exits unless:

`Client.cH == rs/n/c/aD.bI`

so it is active only on the exact Blood Fountain perk-tree interface.

The constructor creates **27** perk entries. Exact surviving names include:

- Blood vengeance I / II;
- Treasure hunter I / II;
- Blood whip;
- Blood rune c'bow;
- Blood dark bow;
- Diamonds are forever;
- Bloodthirsty I / II;
- Killjoy I / II;
- Blood pool;
- Blood staff;
- Blood ring;
- Treasure buddy;
- Emblem snatcher;
- Augury;
- Rigour;
- Bloodlust;
- Excavator;
- War diamonds;
- Unholy smite;
- Eternal recoil;
- Eternal blood cape;
- Vampiric damage;
- Vampiric defence.

The overlay lazily loads exactly:

- `fountain/sprite 1`;
- `fountain/sprite 2`;
- `fountain/sprite 3`.

It draws every perk at its stored interface-relative coordinates, switches sprite state for
the selected/perk-state value, and hit-tests each node over a **32 x 32** region.

Hovering a node pushes that exact perk label into the client hover/prompt path.

Selection writes the exact command:

`::selectperk <index>`

The initial unset state likewise writes:

`::selectperk 0`

and external methods toggle each entry's presentation state or set the selected index.

## Naming boundary

`BloodFountainPerkEntry` is descriptive at **0.998** because its field meanings are
recovered through the exclusive exact consumer rather than surviving developer field names.

`BloodFountainPerkSelectionOverlay` is **0.999** because the existing
`BloodFountainPerkTreeInterface` identity, exact 27-perk vocabulary, dedicated
`fountain/sprite` family and exact `::selectperk` interaction path all agree.

Neither name is claimed as an original stripped source identifier.

R171 remains class-only.

## Acceptance boundary

Chat 2 does not promote R171. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_C2229E2B5CBEFAA12B55`.
