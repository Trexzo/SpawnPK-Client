# Chat 2 — exact-v308 asset updater family R65

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R65 is a separate non-canonical class-only semantic review batch for the client's
self-describing asset-update subsystem.

## Deterministic review result

- candidate classes: **8**
- resolved proposals: **8**
- unresolved: **0**
- review ID: `SEMREVIEW_FB70227883B059A9D489`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/cache/b/a/a` -> `CLIENT_CLASS_000087`
- `rs/cache/b/a/b` -> `CLIENT_CLASS_000088`
- `rs/cache/b/a/c` -> `CLIENT_CLASS_000089`
- `rs/cache/b/a/d` -> `CLIENT_CLASS_000090`
- `rs/cache/b/b` -> `CLIENT_CLASS_000091`
- `rs/cache/b/c` -> `CLIENT_CLASS_000092`
- `rs/cache/b/d` -> `CLIENT_CLASS_000093`
- `rs/cache/b/e` -> `CLIENT_CLASS_000094`

## Shared updater contract

`rs/cache/b/d` -> `AssetUpdater`

This abstract base owns the updater display name, Client reference and error list. It
provides the shared directory/version/ZIP/file handling used by each concrete updater and
defines abstract update/version/policy hooks.

`rs/cache/b/e` -> `AssetVersion`

This class encapsulates the version key and local version-file state. It reads the remote
`versions.txt` data, reads/writes local `versions.dat` state and exposes the remote/local
version values compared by the coordinator.

`rs/cache/b/b` -> `AssetUpdateError`

This exact enum contains the surviving values:

- `INVALID_REMOTE_VERSION`
- `ERROR_DOWNLOADING`

with corresponding user-facing version-check and game-asset-download failure messages.

## Concrete updaters

`rs/cache/b/a/a` -> `CacheUpdater`

- base display name: `Cache`
- version key: `cache_version`
- progress text: `Downloading main game assets..`
- downloads/extracts the main cache bundle while leaving the separately managed sprites
  and configs trees to their sibling updaters.

`rs/cache/b/a/b` -> `ClientUpdater`

- version key: `client_version`
- progress text: `Downloading client..`
- downloads the client update artifact into the local client-update destination.

`rs/cache/b/a/c` -> `ConfigUpdater`

- base display name: `Configs`
- version key: `config_version`
- progress text: `Downloading game configs..`

`rs/cache/b/a/d` -> `SpriteUpdater`

- base display name: `Sprites`
- version key: `sprite_version`
- progress text: `Downloading sprites..`

## Coordinator

`rs/cache/b/c` -> `AssetUpdateCoordinator`

The coordinator constructs the Cache, Sprite and Config updaters, binds the Client into
them and checks their remote/local AssetVersion values.

Surviving text includes:

- `Please wait, checking assets..`
- `Updating outdated game asset: ...`
- `Error with the cache updater!`
- `Error with the sprite updater!`
- `Error with configuration updater!`

That fixes its role as the orchestration layer over the concrete asset updaters.

## Naming boundary

These are semantic recovery names grounded in exact self-labels, version keys and behavior.
Chat 2 does not promote them automatically.

## Acceptance boundary

Main/Core may accept any R65 subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_FB70227883B059A9D489`.
