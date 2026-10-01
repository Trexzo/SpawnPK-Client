# Chat 2 — exact-v308 skills and combat-style interfaces R447

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/aQ` -> `CLIENT_CLASS_000592` -> `SkillsInterface`
- `rs/n/c/aY` -> `CLIENT_CLASS_000600` -> `CombatStylesInterface`
- review: `SEMREVIEW_0859CB2145E0C39C454C`

## SkillsInterface

The builder directly extends R436 `CustomInterfaceBuilder`.

Exact behavior/literals include:

- root widget 3917;
- `skills/SKILL` resources;
- `Total Level: 0`;
- the full exact skill-name set from Attack through Summoning;
- per-skill level and hover/value surfaces.

This is presentation authority only; XP formulas and server-owned skill progression are not inferred.

## CombatStylesInterface

The builder configures multiple weapon-style interface roots and their selectable style controls.

Exact literals include:

- `Chop`, `Hack`, `Smash`, `Block`
- `Stab`, `Lunge`, `Slash`
- `Pound`, `Pummel`, `Spike`, `Swipe`
- `Accurate ... Attack XP`
- `Aggressive ... Strength XP`
- `Controlled ... Shared XP`
- `Defensive ... Defence XP`

The class is therefore the client combat-style interface catalogue rather than a single weapon-specific screen.

## Boundary

R447 names client presentation builders only. No combat formulas, accuracy rules, XP rates or
server action authority is claimed.

R447 remains non-canonical Chat 2 research only.
