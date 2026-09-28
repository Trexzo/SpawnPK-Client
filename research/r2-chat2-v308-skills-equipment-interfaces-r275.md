# Chat 2 — exact-v308 skills/equipment interfaces R275

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/I` -> `CLIENT_CLASS_000554` -> `EquipmentInterface`
- `rs/n/c/aQ` -> `CLIENT_CLASS_000592` -> `SkillsInterface`
- review: `SEMREVIEW_ECFB373576C098CE1BAD`
- unresolved: **0**
- field/method proposals: **0**

## Equipment interface

Exact v308 modifies the equipment root at interface **1644** and adds:

- `equipment/BOX`
- **Show Equipment Stats**
- **Show Items Kept on Death**
- `equipment/outline`
- a **Remove** action

This is the main equipment presentation surface, distinct from the already-reviewed `EquipmentStatsInterface`.

## Skills interface

Exact v308 builds the `skills/SKILL` surface with **Total Level: 0**, a 24-skill grid, and the full skill-domain labels including combat skills plus Mining, Agility, Smithing, Herblore, Fishing, Cooking, Prayer, Crafting, Firemaking, Magic, Fletching, Woodcutting, Runecrafting, Slayer, Farming, Construction, Hunter and Summoning.

These are descriptive semantic names backed by exact-v308 behavior and resources. No original stripped identifier is claimed.

## Boundary

R275 remains non-canonical. Chat 2 performs no semantic acceptance or rewrite.
