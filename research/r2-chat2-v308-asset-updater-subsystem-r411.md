# Chat 2 — exact-v308 asset updater subsystem R411

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Recovered live updater family

- `rs/cache/b/a/a` -> 000087 -> `CacheUpdater`
- `rs/cache/b/a/c` -> 000089 -> `ConfigUpdater`
- `rs/cache/b/a/d` -> 000090 -> `SpriteUpdater`
- `rs/cache/b/b` -> 000091 -> `AssetUpdateError`
- `rs/cache/b/c` -> 000092 -> `AssetUpdateManager`
- `rs/cache/b/d` -> 000093 -> `AssetUpdater`
- `rs/cache/b/e` -> 000094 -> `AssetVersionTracker`

Review: `SEMREVIEW_1488388A9570A04E4674`

## Manager and strategies

`AssetUpdateManager` constructs exactly three live updater strategies:

- Cache
- Sprites
- Configs

It checks each updater's remote/local version pair, runs required updates and emits surviving
diagnostics such as:

- `Error with the cache updater!`
- `Error with the sprite updater!`
- `Error with configuration updater!`

## Shared updater contract

`AssetUpdater` centralizes:

- updater display name;
- errors;
- Client ownership;
- remote/local version checks;
- ZIP extraction;
- update-needed comparison.

## Version tracking

`AssetVersionTracker` owns one version key and one local version-file path. It:

- reads the remote version manifest;
- extracts the requested keyed version;
- reads the local keyed version;
- writes the updated local version after success;
- shows the connection-help dialog when remote version retrieval fails.

The dialog's hyperlink listener is already independently owned by R336 as
`AssetVersionHyperlinkListener` and is therefore excluded from R411.

## Existing authority reconciled

R336 already owns:

- `rs/cache/b/f` -> `CLIENT_CLASS_000095` -> `AssetVersionHyperlinkListener`

The initial R411 draft duplicated this owner under a different listener name. That proposal
has been removed; R336 remains sole authority.

## Withheld classes

- `rs/cache/b/a`: dead/unreferenced callback interface.
- `rs/cache/b/a/b`: client-updater subclass exists but has no incoming exact-v308 reference.

R411 remains non-canonical Chat 2 research.
