# Chat 2 — exact-v308 Loadouts editors R392

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/b/a/A` -> `CLIENT_CLASS_000207` -> `LoadoutSkillLevelEditor`
- `rs/gui/b/a/y` -> `CLIENT_CLASS_000234` -> `LoadoutMetadataEditorDialog`
- review: `SEMREVIEW_460CD0D7FE0225722439`

## Skill-level editor

`rs/gui/b/a/A` is opened by R391's loadout panel click handler with an index 0..6. The
editor maps those indexes exactly to:

- Attack
- Range
- Strength
- Prayer
- Defence
- Magic
- Hitpoints

It owns one editable field and an exact `Apply` action.

## Metadata editor

`rs/gui/b/a/y` owns the loadout name, color and icon editing surface. It is shared by two
independent workflows:

- create: exact text `Name Your Loadout` + `Create`;
- rename: exact title `Rename`, seeded with the existing name/color/icon.

That shared use rules out a narrower create-only or rename-only name.

R392 remains non-canonical semantic research only.
