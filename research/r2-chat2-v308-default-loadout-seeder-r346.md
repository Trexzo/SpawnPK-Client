# Chat 2 — default loadout catalogue seeder R346

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/b/c/a` -> `CLIENT_CLASS_000243` -> `DefaultLoadoutSeeder`
- proposal: `SEMPROP_6A0A032AEC572C703298`
- review: `SEMREVIEW_6660F6C9584453B8CF9E`

## Exact role

The class exposes one substantial static initializer receiving:

- a String persistence/key context;
- R143 `LoadoutFolder`;
- R143 `LoadoutPersistence`.

It first tests whether the target folder is empty. Existing user/persisted content is not
overwritten.

For an empty folder it constructs the built-in default catalogue using only the already
reviewed loadout model graph:

- `LoadoutDefinition`
- `LoadoutEquipmentSlot`
- `LoadoutItemEntry`
- `LoadoutSpellbook`

The exact catalogue contains named presets including `Melee` and `Hybrid (NH)`, with
explicit equipment item IDs, inventory item/quantity records, spellbook state and additional
loadout configuration values.

That fixes the class as the default catalogue seeder rather than a generic item table or
codec.

## Boundary

R346 names initialization behavior only. It does not claim that the preset item choices are
server-authoritative or immutable gameplay policy.

R346 remains non-canonical semantic research only.
