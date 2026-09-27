# Chat 2 — exact-v308 Loadout item-image cache family R260

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/gui/b/g` -> `CLIENT_CLASS_000249` -> `LoadoutItemImageCache`
- `rs/gui/b/b/b` -> `CLIENT_CLASS_000238` -> `LoadoutItemImageLoader`
- review: `SEMREVIEW_6FABA61EA6896533D66A`
- unresolved: **0**
- field/method proposals: **0**

## Exact cache/dispatch behavior

`LoadoutItemImageCache` owns the complete shared item-image state for the reviewed
Loadouts model:

- `ConcurrentHashMap<Integer, rs.gui.x>` keyed by item id;
- a fixed thread pool of **5**;
- an array of **5** loader instances;
- a round-robin loader index;
- one per-instance cached image;
- one `LoadoutItemEntry`.

Lookup first checks the shared cache. On a miss, the item's id is dispatched to one of the
five loaders and the call returns null. On a hit, the image is retained on the instance and
returned.

## Exact loader behavior

`rs/gui/b/b/b` schedules work with the surviving task key:

`LoadoutIco_<itemId>`

Its callback:

1. resolves the item sprite for quantity **1** at **32x32**;
2. converts it to an AWT Image;
3. removes black background pixels;
4. wraps the result in `rs.gui.x`;
5. stores it in `LoadoutItemImageCache`'s shared item-id map;
6. asks the live Launcher to refresh the UI.

The loader has no unrelated exact-v308 consumer outside this loadout image family.

## Naming boundary

Both R260 names are descriptive exact-behavior recoveries. They do not assert original
developer identifiers.

## Acceptance boundary

R260 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
