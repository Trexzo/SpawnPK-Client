# Chat 2 — exact-v308 loadout item entry R333

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/b/f` -> `CLIENT_CLASS_000248` -> `LoadoutItemEntry`
- proposal: `SEMPROP_2472171B1E78D06469F6`
- review: `SEMREVIEW_303BF726CEF0761FC78F`

## Why this old holdout is now resolved

The post-R275 frontier note intentionally withheld this two-int class because the surrounding
Loadouts subsystem was known but the record noun itself was not yet strong enough.

Later retained work closes that gap.

Exact `rs/gui/b/f`:

- has exactly two final int fields;
- constructor `(int,int)` stores both;
- constructor `(int)` stores the first value and defaults the second to **1**;
- exposes one getter for each;
- resolves its item image from the first value through the reviewed loadout image-cache path.

R143 `LoadoutDefinition` stores this exact type in:

- its 28-slot inventory array;
- its `Map<LoadoutEquipmentSlot, ...>`.

R143 `LoadoutPersistence` serializes/deserializes both values for every equipment and
inventory entry.

R277 clone-current-equipment constructs entries from live widget item-id and quantity state.

The exact spawn workflow reads:

- first value as item id;
- second value as quantity.

R260 `LoadoutItemImageCache` is constructed around this exact type and already identifies
it as `LoadoutItemEntry` in its retained evidence.

## Boundary

`LoadoutItemEntry` is now a conservative exact-behavior name fixed by the complete model,
persistence, clone, spawn and image-cache graph. No field/member proposals are added.

R333 remains non-canonical semantic research only.
