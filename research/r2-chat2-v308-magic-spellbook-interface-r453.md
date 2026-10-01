# Chat 2 — exact-v308 magic spellbook interface R453

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/ap` -> `CLIENT_CLASS_000617` -> `MagicSpellbookInterface`
- proposal: `SEMPROP_0CCBC44D6E08115D1392`
- review: `SEMREVIEW_C0A57745722277EC9859`

## Exact spellbook/filter surface

The class extends the recovered custom-interface builder and owns the 41900-series magic
presentation/filter state.

Exact controls include:

- `Magic spellbook filter`
- `Spell Filters`
- `Show Combat spells`
- `Show Teleport spells`
- `Show Utility spells`
- the low-level spell visibility filter

The same builder contains presentation metadata for broad spell families including:

- surge spells;
- miasmic spells;
- lunar/utility spells such as Vengeance, Plank Make, NPC Contact, Stat Spy, Cure/Heal,
  potion share, Superglass Make and Spellbook Swap;
- rune labels;
- home/PK/training/money-making/boss/minigame teleport categories.

This is therefore the shared magic spellbook/presentation catalogue, not a single custom
spell feature.

## Live ownership

Exact-v308 reverse references include:

- `rs/Client`;
- central interface registry/construction;
- live render/input code;
- the class's own filter/state inner types.

## Boundary

R453 recovers client presentation only. Spell legality, rune consumption, combat formulas,
effects and server-side execution remain server authority.

R453 remains non-canonical Chat 2 research only.
