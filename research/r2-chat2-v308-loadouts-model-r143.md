# Chat 2 — exact-v308 Loadouts model and persistence R143

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R143 is a separate non-canonical class-only review for the core model and persistence layer
behind the already-reviewed `LoadoutFolderPanel`.

## Deterministic review result

- candidate classes: **6**
- resolved proposals: **6**
- unresolved: **0**
- review ID: `SEMREVIEW_A53593714C8C3335E7B8`
- field/method proposals: **0**

## Stable IDs

- `rs/gui/b/a` -> `CLIENT_CLASS_000205` -> `LoadoutDefinition`
- `rs/gui/b/a$a` -> `CLIENT_CLASS_000206` -> `LoadoutSpellbook`
- `rs/gui/b/b/d` -> `CLIENT_CLASS_000240` -> `LoadoutPersistence`
- `rs/gui/b/c` -> `CLIENT_CLASS_000242` -> `LoadoutFolder`
- `rs/gui/b/c/c` -> `CLIENT_CLASS_000245` -> `LoadoutEquipmentSlot`
- `rs/gui/b/d` -> `CLIENT_CLASS_000246` -> `LoadoutManager`

## LoadoutDefinition

The live Loadouts panel creates one `rs/gui/b/a` per named loadout.

The record owns:

- user-visible loadout name;
- color/icon presentation metadata;
- one spellbook selection;
- prayer state;
- **28** item slots;
- an equipment-slot map;
- **7** skill values.

The exact spawn action retrieves the active record from `rs/gui/b/d` and serializes it into:

- `::item_loadout`;
- `::skills_loadout`;
- `::normalpray` or `::cursespray`;
- the selected spellbook state.

The live button label is exactly:

`Spawn this loadout in-game`

This fixes the class as one loadout definition rather than a generic item container.

## LoadoutSpellbook

`rs/gui/b/a$a` preserves exact enum constants:

- `LUNAR`;
- `ANCIENTS`;
- `MODERN`.

Each value carries the matching visible label and asset:

- Lunar -> `/assets/gui/lunar.png`;
- Ancients -> `/assets/gui/ancients.png`;
- Modern -> `/assets/gui/modern.png`.

`LoadoutDefinition` stores the enum and the exact spawn path consumes its label.

## LoadoutFolder

`rs/gui/b/c` extends:

`ArrayList<rs/gui/b/a>`

Its only own state is one immutable folder-name String.

The manager stores these values by folder name and applies exact folder semantics including
rename/delete/reorder and the requirement that a folder retain at least one loadout.

## LoadoutManager

`rs/gui/b/d` extends:

`LinkedHashMap<String, rs/gui/b/c>`

and separately tracks:

- current folder name;
- active loadout.

Its complete API handles:

- folder create/rename/delete/reorder;
- loadout create/select/rename/delete/reorder;
- name validation;
- panel refresh;
- persistence synchronization.

Exact validation text includes:

- `You already have a folder with this name!`;
- `You already have a loadout with this name!`;
- `You already have that name in this folder!`;
- `You can't delete your only folder!`;
- `You can't delete the only loadout on your folder!`.

The exact spawn action retrieves the active definition from this manager.

## LoadoutPersistence

`rs/gui/b/b/d` is the file-backed persistence layer.

It reads/writes:

- `order.settings`;
- per-folder `.settings` files.

It loads folder order, serializes folder contents, reconstructs `LoadoutFolder` and
`LoadoutDefinition` objects, restores spellbook/prayer/skill/equipment/inventory state and
deletes the corresponding files when a folder is removed.

Its diagnostics explicitly identify the Loadouts domain, including invalid or missing folder
entries while reading the order configuration.

## LoadoutEquipmentSlot

`rs/gui/b/c/c` preserves exact enum constants:

- `HELMET`;
- `AMULET`;
- `CHEST`;
- `LEGS`;
- `FEET`;
- `CAPE`;
- `ARROWS`;
- `SHIELD`;
- `WEAPON`;
- `GLOVES`;
- `RING`.

Each value binds an equipment index/position to its matching slot image such as
`slot_helm.png`, `slot_chest.png`, `slot_wep.png` and `slot_ring.png`.

The loadout spawn path serializes this map separately from the 28 backpack item slots.

## Deliberate exclusion

`rs/gui/b/f` remains unnamed.

It is an exact two-integer item-id/quantity pair used by loadout inventory/equipment state,
but R143 does not impose a narrower conventional noun such as `ItemStack` when the binary
does not preserve one.

## Naming boundary

All six names are descriptive readable recovery for the exact Loadouts subsystem.

The user-facing noun `Loadouts` survives in the live tab and file diagnostics, while the
class responsibilities are fixed by collection shape, exact enum constants, persistence
files and active spawn consumers.

No name is claimed as an original developer identifier.

## Acceptance boundary

Chat 2 does not promote R143. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_A53593714C8C3335E7B8`.
