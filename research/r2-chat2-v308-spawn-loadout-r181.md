# Chat 2 — exact-v308 Spawn Loadout control/action R181

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R181 is a separate non-canonical class-only review for the exact loadout spawn button factory
and its dedicated action listener.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_1B0ECB200EAB7BE90A8F`
- field/method proposals: **0**

## Stable IDs

- `rs/gui/b/a/B` -> `CLIENT_CLASS_000208` -> `SpawnLoadoutButtonFactory`
- `rs/gui/b/a/C` -> `CLIENT_CLASS_000209` -> `SpawnLoadoutAction`

## SpawnLoadoutButtonFactory

The factory creates exactly one Swing button with:

- label `Spawn Loadout`;
- tooltip `Spawn this loadout in-game`;
- icon `assets/gui/loadout.png`.

It attaches only `rs/gui/b/a/C`, passing the owning loadout panel.

That parent belongs to the existing reviewed loadout graph from R143/R144, including
`LoadoutDefinition`, `LoadoutManager`, `LoadoutFolder`,
`LoadoutEquipmentSlot` and loadout presentation classes.

## SpawnLoadoutAction

The action first requires a live/ready client and then obtains the selected
`LoadoutDefinition`.

If no loadout is selected, exact v308 shows:

`You don't have a loadout selected!`

For a selected loadout it serializes the complete spawn state.

Exact command prefixes include:

- `::item_loadout`;
- `::equip_loadout`;
- `::pet_loadout`;
- `::skills_loadout`;
- `::normalpray`;
- `::cursespray`.

The action enumerates:

- the full item/inventory array;
- every `LoadoutEquipmentSlot`;
- pet selection;
- loadout skill values;
- `LoadoutSpellbook`;
- prayer mode.

It then writes only the corresponding client loadout command/state fields.

## Naming boundary

No matching public source identifier was found for these custom SpawnPK classes.

The names therefore remain descriptive, but their whole-class responsibilities are exact:
the button literally says `Spawn Loadout`, and its sole listener serializes the complete
selected loadout spawn protocol.

Both proposals are **0.999** and remain non-canonical.

## Acceptance boundary

Chat 2 does not promote R181. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_1B0ECB200EAB7BE90A8F`.
