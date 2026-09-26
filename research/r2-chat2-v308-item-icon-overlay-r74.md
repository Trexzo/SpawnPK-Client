# Chat 2 — exact-v308 item icon overlay semantics R74

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R74 is a separate non-canonical class-only semantic review batch for the exact per-item
icon-overlay descriptor used by item/interface rendering.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_1EDA94B7784633DD0C3D`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/d/n` -> `CLIENT_CLASS_000125`
- `rs/d/n$a` -> `CLIENT_CLASS_000126`

## `rs/d/n$a` -> `ItemIconOverlayType`

This exact enum preserves two constants:

- `TEXT_ICON`
- `ITEM_ICON`

The outer descriptor uses the enum to choose how its overlay sprite is resolved.

TEXT_ICON selects a sprite from the client's text-icon sprite set, including the exact
text-icon remapping table when present.

ITEM_ICON resolves the configured reference as another item id and asks R28
`ItemDefinition` to generate that item's sprite.

## `rs/d/n` -> `ItemIconOverlay`

Each descriptor owns:

- the overlay type;
- the referenced text-icon or item id;
- x offset;
- y offset.

A static registry is keyed by the base item id.

The item-definition update/config path contains the exact icon-related keys:

- `icon`
- `iconitem`
- `iconoffsets`
- `iconx`
- `icony`

and constructs a TEXT_ICON or ITEM_ICON descriptor with the configured offsets.

The item/interface rendering path then checks whether the current item id has a registered
descriptor and draws the resolved overlay sprite at the base item's screen position plus
those x/y offsets.

That exact config -> descriptor -> sprite-resolution -> render chain fixes the semantic
identity as `ItemIconOverlay`.

## Naming boundary

Both names are semantic recovery names. R74 does not claim they are verbatim original
SpawnPK developer identifiers.

## Acceptance boundary

Chat 2 does not promote R74. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_1EDA94B7784633DD0C3D`.
