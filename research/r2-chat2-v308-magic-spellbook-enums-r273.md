# Chat 2 — exact-v308 MagicSpellbookInterface nested enums R273

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/ap$a` -> `CLIENT_CLASS_000618` -> `MagicSpellCategory`
- `rs/n/c/ap$b` -> `CLIENT_CLASS_000619` -> `MagicSpell`
- `rs/n/c/ap$c` -> `CLIENT_CLASS_000620` -> `MagicSpellbook`
- review: `SEMREVIEW_BE970351A4DEBF7D9618`
- unresolved: **0**
- field/method proposals: **0**

## Exact-v308 evidence

The enclosing `rs/n/c/ap` is already accepted by Main/Core as `MagicSpellbookInterface`.

The nested category enum preserves all three names directly:

- `COMBAT`
- `TELEPORT`
- `UTILITY`

The individual-spell enum preserves **41** spell names directly, including `AIR_STRIKE`, `CONFUSE`, elemental bolt/blast/wave/surge spells, `SARA_STRIKE`, `GUTHIX_CLAWS`, `ZAMMY_FLAMES`, `TELEBLOCK`, and the custom teleport entries `HOME_TELEPORT`, `MONEY_TELEPORT`, `SKILL_TELEPORT`, `BOSS_TELEPORT`, `PK_TELEPORT`, `MINIGAME_TELEPORT`, `HOUSE_TELEPORT`, and `BOUNTY_TELEPORT`.

Each spell value stores two integers plus the category enum. The accepted parent resolves spell values by widget ID, reads their category, and compares the second integer to the player's magic level.

The spellbook enum preserves:

- `MODERN`
- `LUNAR`
- `ANCIENTS`

The accepted parent iterates those values and dispatches its spellbook-specific update/layout path through them.

## Boundary

R273 is non-canonical research only. Chat 2 does not accept or rewrite any class.
