# Chat 2 — source-proven cache updater/download family R408

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Recovered source-map authority supplies exact source identities for the remaining cache
download/update family. R23 already owns `AssetVersion`; R405 already owns
`BrowserHyperlinkListener`.

## Recovered classes

- `rs/cache/a/a` / 000083 -> `ClientFileDownloader`
- `rs/cache/a/b` / 000084 -> `FileDownloader`
- `rs/cache/b/a` / 000086 -> `ProgressListener`
- `rs/cache/b/a/a` / 000087 -> `CacheUpdater`
- `rs/cache/b/a/b` / 000088 -> `ClientUpdater`
- `rs/cache/b/a/c` / 000089 -> `ConfigUpdater`
- `rs/cache/b/a/d` / 000090 -> `SpriteUpdater`
- `rs/cache/b/b` / 000091 -> `AssetUpdateError`
- `rs/cache/b/c` / 000092 -> `AssetUpdaterManager`
- `rs/cache/b/d` / 000093 -> `AssetUpdater`

Review: `SEMREVIEW_394BCDBC45C3C65E6DF6`

## Exact-v308 corroboration

`FileDownloader` owns URL/File state, streams HTTP content to disk, tracks bytes/content
length and invokes an abstract progress hook. `ClientFileDownloader` extends it and reports
percentage/speed text back through Client.

The updater side contains one progress-listener interface, shared AssetUpdater base/error
enum/manager and four concrete asset updaters. ConfigUpdater and SpriteUpdater preserve
particularly strong literals: `config_version`, `sprite_version`, `Configs`, `Sprites`,
`Downloading game configs..` and `Downloading sprites..`.

## Boundary

This is source-proven class identity only. No updater policy or server/update endpoint is
promoted as canonical behavior by Chat 2.

R408 remains non-canonical semantic research only.
