# Chat 2 — exact-v308 game asset updater semantics R23

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R23 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R22 review batches.

## Deterministic review result

- candidate classes: **10**
- resolved proposals: **10**
- unresolved: **0**
- review ID: `SEMREVIEW_A7557C36D92989848D7C`
- field/method proposals: **0**

## Download primitives

- `rs/cache/a/b` -> `FileDownloader`
- `rs/cache/a/a` -> `ClientProgressFileDownloader`

The generic downloader owns a URL and destination File, streams the download in 16 KiB
chunks, tracks byte count/content length/start time and invokes an abstract progress
callback.

The client-aware subclass adds the exact SpawnPK Client loading UI and reports percentage
plus transfer rate in `kb/s` or `mb/s`.

## Versioned asset-update framework

- `rs/cache/b/b` -> `AssetUpdateError`
- `rs/cache/b/c` -> `AssetUpdateManager`
- `rs/cache/b/d` -> `AssetUpdater`
- `rs/cache/b/e` -> `AssetVersion`

Exact evidence includes:

- user-facing version-check and game-asset download error enum messages;
- `Please wait, checking assets..`;
- `Updating outdated game asset:`;
- local `versions.dat` and remote `versions.txt`;
- key/value version rewrite logic;
- common ZIP extraction, version parsing, updater display name, Client injection and
  per-updater error storage.

The manager constructs and coordinates the cache, sprite and config updaters, compares
local/remote versions, invokes updates and reports failures.

## Concrete updaters

- `rs/cache/b/a/a` -> `CacheUpdater`
- `rs/cache/b/a/b` -> `ClientUpdater`
- `rs/cache/b/a/c` -> `ConfigUpdater`
- `rs/cache/b/a/d` -> `SpriteUpdater`

Exact roles:

### CacheUpdater

- display name: `Cache`
- version key: `cache_version`
- archive: `cache.zip`
- progress label: `Downloading main game assets..`
- extracts the main cache while preserving separately managed sprite/config directories.

### ClientUpdater

- version key: `client_version`
- downloads `/assets/client.jar`
- progress label: `Downloading client..`
- verifies the resulting client JAR exists.

### ConfigUpdater

- display name: `Configs`
- version key: `config_version`
- archive: `configs.zip`
- progress label: `Downloading game configs..`.

### SpriteUpdater

- display name: `Sprites`
- version key: `sprite_version`
- archive: `sprites.zip`
- progress label: `Downloading sprites..`.

## Boundary

R23 deliberately stops at the versioned game-asset updater subsystem. The older low-level
cache-file/network engine under adjacent `rs/cache/*` classes is separate and remains
unnamed until its identities are proven independently.

Chat 2 does not promote R23. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_A7557C36D92989848D7C`.
