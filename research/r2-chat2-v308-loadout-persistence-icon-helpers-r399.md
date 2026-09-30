# Chat 2 — loadout persistence/icon helpers R399

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/b/b/b` -> `CLIENT_CLASS_000238` -> `LoadoutItemIconLoader`
- `rs/gui/b/b/c` -> `CLIENT_CLASS_000239` -> `LoadoutBinaryCodec`
- `rs/gui/b/c/a` -> `CLIENT_CLASS_000243` -> `DefaultLoadoutSeeder`
- `rs/gui/b/g` -> `CLIENT_CLASS_000249` -> `LoadoutItemIconCache`

Review: `SEMREVIEW_9A96CDC42F857F4215CC`

## Binary codec

R143 `LoadoutPersistence` owns paths/files and delegates actual binary payload encoding to
`rs/gui/b/b/c`.

The writer serializes the LoadoutDefinition's user-visible metadata and runtime loadout data
to DataOutputStream; the reader rebuilds persisted folder/loadout state from DataInputStream.

This separation fixes `LoadoutBinaryCodec` rather than another persistence-manager name.

## Default seeder

`rs/gui/b/c/a` only seeds when the target folder is empty.

It creates fixed starter presets including:

- `Melee`
- `Hybrid (NH)`
- `Pure`

and fills them with hardcoded loadout equipment/item/spellbook/prayer/default metadata before
normal persistence/UI refresh.

## Icon cache

`rs/gui/b/g` owns:

- ConcurrentHashMap<itemId, rendered icon>
- fixed five-thread executor
- five loader workers
- round-robin miss dispatch.

R144 `LoadoutItemEntry` asks it for the item's rendered icon.

## Icon loader

`rs/gui/b/b/b` receives item ids from the cache, renders a 32x32 item sprite, converts it
into the UI image wrapper, stores it in the shared cache and triggers refresh.

## Explicitly withheld neighboring classes

- `rs/gui/b/b`
- `rs/gui/b/b/a`
- `rs/gui/b/b/e`

have no live exact-v308 references sufficient to justify semantic names, so R399 leaves them
untouched.

R399 remains non-canonical semantic research only.
