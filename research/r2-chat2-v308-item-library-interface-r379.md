# Chat 2 — Official SpawnPK Item Library R379

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/ab` -> `CLIENT_CLASS_000603` -> `ItemLibraryInterface`
- proposal: `SEMPROP_6874406B47241F558794`
- review: `SEMREVIEW_875277F48B818C9E8E36`

## Exact identity

The class builds root widget **47500** and preserves the exact title:

`Official SpawnPK Item Library`

The same interface owns:

- selected item-guide title/state;
- `ITEM_GUIDE_SELECTED_*` keys;
- `wiki/item` assets;
- category and description rendering;
- `Search by item`;
- `<img=39> Search for an item`;
- `View equipment bonuses`;
- attack/defence bonus rows for Stab, Slash, Crush, Magic and Range.

This is therefore the root Item Library interface rather than a search-only helper.

## Boundary

The proposal names only the exact client presentation/interface role. It does not promote
item-stat values into server authority.

R379 remains non-canonical class-only semantic research.
