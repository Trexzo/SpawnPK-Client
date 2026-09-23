# Chat 2 — exact-v308 SPK Editor Kit command handlers R108

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R108 is a separate non-canonical class-only review for the two typed command processors
dispatched by R107 `EditorKitController`.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_63C315F8C41329C08B7B`
- field/method proposals: **0**
- confidence: **0.998** each

## Stable IDs

- `rs/l/b/a/b` -> `CLIENT_CLASS_000373` -> `EditorNpcCommandHandler`
- `rs/l/b/a/c` -> `CLIENT_CLASS_000377` -> `EditorPlayerCommandHandler`

## EditorNpcCommandHandler

EditorKitController dispatches here only when the selected entity is an
`EditorNpcEntity`.

The helper's static command vocabulary is:

- `reset`
- `select`
- `set`
- `set_id`
- `setid`
- `setnpc`
- `sizex`
- `stand`
- `walk`

It changes the NPC definition/id and NPC-oriented animation/size state, then refreshes the
entity model/render state.

The transform path emits:

`@whi@<img=24> Entity transformed to @gre@... (...)!`

through EditorKitController output.

## EditorPlayerCommandHandler

EditorKitController dispatches here only when the selected entity is an
`EditorPlayerEntity`.

Its exact equipment aliases cover:

- weapon / wep;
- cape / back;
- legs / leg;
- gloves / glove / hand / hands;
- boots / boot / feet;
- shield;
- helmet / helm / hat / head;
- amulet / ammy / neck;
- chest / body / top.

It also supports:

- `male`
- `female`
- full body/chest/hat/helm/mask flags and aliases
- reset/off behavior.

Surviving feedback includes:

- `Set player weapon!`
- `Set player cape!`
- `Set player legs!`
- `Entity transformed to male!`
- `Entity transformed to female!`

## Naming boundary

Both names are descriptive exact-behavior recovery names. No original source nouns are
claimed.

R108 deliberately does not include the Editor Kit notification, comparator or model/debug
support classes.

## Acceptance boundary

Chat 2 does not promote R108. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_63C315F8C41329C08B7B`.
