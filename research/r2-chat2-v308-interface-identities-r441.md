# Chat 2 — exact-v308 attack-options interface R441

Exact client authority: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Retained result

- `rs/n/c/f` -> `CLIENT_CLASS_000659` -> `AttackOptionsInterface`
- proposal: `SEMPROP_C82F73B1BFBC139069AA`
- review: `SEMREVIEW_B4A84A5291A1C3D5A7F7`

The class extends R436 `CustomInterfaceBuilder` and builds the exact sections:

- `<u>Player attack options`
- `<u>NPC/Bot attack options`

It also owns the exact toggle:

- `Always right-click clan members`

Exact v308 references it from `CustomInterfaceRegistry` and `rs/l/b/a`.

## Removed attempted duplicates

The original R441 attempt also proposed three already-owned classes:

- `rs/n/c/al` / 000613 / `ItemLoadoutModificationInterface` — already R3.
- `rs/n/c/w` / 000676 — already R3 as `ComponentColorSelectionInterface`.
  The later attempted `TextColorSelectionInterface` name was not retained because the owner
  already has earlier semantic authority.
- `rs/n/c/aq` / 000621 — already R5 as `MakeQuantityInterface`.
  The later attempted `MakeQuantitySelectionInterface` alias was not retained.

R441 therefore contains exactly one non-canonical class proposal.
