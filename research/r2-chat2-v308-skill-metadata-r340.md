# Chat 2 — exact-v308 skill metadata R340

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/f/e` -> `CLIENT_CLASS_000175` -> `SkillMetadata`
- proposal: `SEMPROP_B1486B8B0FC8E48F7450`
- review: `SEMREVIEW_BD279051F7AC442AE739`

## Exact static metadata

The class defines 24 skills in exact client index order:

Attack, Defence, Strength, Hitpoints, Ranged, Prayer, Magic, Cooking, Woodcutting,
Fletching, Fishing, Firemaking, Crafting, Smithing, Mining, Herblore, Agility,
Thieving, Slayer, Farming, Runecraft, Construction, Hunter, Summoning.

It owns:

- skill count = 24;
- lowercase protocol/internal names;
- display names plus exact associated widget IDs;
- the per-index boolean inclusion table;
- static integer skill-index constants.

## Independent live consumers

### Client

Client uses the table to:

- size multiple live per-skill arrays;
- gate skill aggregation through the boolean table;
- resolve skill presentation/widget IDs from the metadata matrix.

### Skill event bridge

`rs/s/h/a` consumes `rs/f/e.b[skillId]` from live `SkillLevelChanged` events to
derive the skill name used by its notification/presentation flow.

## Boundary

R275 already names `rs/n/c/aQ` as `SkillsInterface`. That is the visible UI builder.

R340 names the independent static metadata/index authority and does not duplicate the UI role.

R340 remains non-canonical semantic research only.
