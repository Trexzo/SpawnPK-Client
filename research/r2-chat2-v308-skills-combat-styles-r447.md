# Chat 2 — exact-v308 Skills interface R447

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Corrected result

R447 retains:

- `rs/n/c/aQ` -> `CLIENT_CLASS_000592` -> `SkillsInterface`
- review: `SEMREVIEW_E2D828CD52E864C46855`

The attempted `rs/n/c/aY -> CombatStylesInterface` proposal was removed after R2 reconciliation.
R2 already owns the same class as `CombatStyleInterface`; the later exact style/XP literals are
corroboration, not new ownership.

## SkillsInterface

Exact behavior/literals include:

- root widget 3917;
- `skills/SKILL` resources;
- `Total Level: 0`;
- the complete skill-name presentation from Attack through Summoning;
- per-skill level/hover surfaces.

The stable ID is canonical R1 `seed_lineage()` authority.

## Boundary

R447 is client presentation recovery only. XP formulas and server progression remain outside
this layer.

R447 remains non-canonical Chat 2 research only.
