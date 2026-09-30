# Chat 2 — R406 duplicate downloader audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R406 retains **no semantic proposal**.

The attempted downloader batch was rejected during duplicate reconciliation because R23
already owns both exact classes:

- `rs/cache/a/a`
  - `CLIENT_CLASS_000083`
  - `ClientProgressFileDownloader`
  - R23 proposal `SEMPROP_E55C813850CE7A2BF7FD`

- `rs/cache/a/b`
  - `CLIENT_CLASS_000084`
  - `FileDownloader`
  - R23 proposal `SEMPROP_637A82D9F4FA393DDAB6`

R23 also already owns the surrounding updater subsystem:

- `rs/cache/b/a/a` -> `CacheUpdater`
- `rs/cache/b/a/b` -> `ClientUpdater`
- `rs/cache/b/a/c` -> `ConfigUpdater`
- `rs/cache/b/a/d` -> `SpriteUpdater`
- `rs/cache/b/b` -> `AssetUpdateError`
- `rs/cache/b/c` -> `AssetUpdateManager`
- `rs/cache/b/d` -> `AssetUpdater`
- `rs/cache/b/e` -> `AssetVersion`

## New corroborating evidence

The direct exact-v308 re-audit independently reconfirmed the R23 semantics:

- the base downloader streams URL data to a destination File in 16 KiB chunks;
- the client-aware subclass computes percent and kb/s/mb/s and calls the Client progress UI;
- the same subclass is used for main game assets, client.jar, configs and sprites.

This strengthens R23 but does not create a second semantic identity.

## Boundary

R406 is a correction/corroboration note only.

No candidate JSON, semantic-review JSON, deterministic proposal test, acceptance spec or
source rewrite is retained.
