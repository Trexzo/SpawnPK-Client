# Chat 2 — exact-v308 skill definitions R352

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/f/e` -> `CLIENT_CLASS_000175` -> `SkillDefinitions`
- proposal: `SEMPROP_F1FF2B1ADC953969AD3D`
- review: `SEMREVIEW_F82DD6E453C4CD26D798`

## Exact static catalog

`rs/f/e` owns the central skill metadata arrays.

The exact skill count is **24**.

The lowercase ordered skill names are:

- attack
- defence
- strength
- hitpoints
- ranged
- prayer
- magic
- cooking
- woodcutting
- fletching
- fishing
- firemaking
- crafting
- smithing
- mining
- herblore
- agility
- thieving
- slayer
- farming
- runecraft
- construction
- hunter
- summoning

A parallel metadata table contains the presentation label and exact skill-interface widget ID
for each skill, including examples:

- Attack -> 50023
- Defence -> 50065
- Construction -> 50215
- Hunter -> 50225
- Summoning -> 50235

The class also owns the parallel enabled-skill boolean table.

## Live consumers

Exact v308 `Client`:

- sizes multiple skill-state arrays from the class skill count;
- checks the enabled-skill flags when iterating skills;
- indexes the metadata table for skill-interface presentation.

The live skill-level-change plugin path reads the same lowercase names to derive display
labels for combat-boost infoboxes.

## Naming boundary

The class is static metadata, not player skill state and not server skill-rule authority.
Accordingly R352 uses `SkillDefinitions`, not `SkillManager`.

R352 remains non-canonical semantic research only.
