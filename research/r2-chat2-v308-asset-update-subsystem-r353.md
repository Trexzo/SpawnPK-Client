# Chat 2 — asset update subsystem R353

Exact client authority: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Recovered:
- `rs/cache/b/a/a` / 000087 -> `MainGameAssetUpdater`
- `rs/cache/b/a/c` / 000089 -> `ConfigAssetUpdater`
- `rs/cache/b/a/d` / 000090 -> `SpriteAssetUpdater`
- `rs/cache/b/c` / 000092 -> `AssetUpdateManager`
- `rs/cache/b/d` / 000093 -> `AssetUpdater`
- `rs/cache/b/e` / 000094 -> `AssetVersion`

Review: `SEMREVIEW_BCB4AD69A3EE0D86ADFB`.

The abstract updater owns common remote/local version checking, URL download, directory creation and ZIP extraction. Its three exact concrete subclasses retain explicit asset names and download strings: Cache/main game assets, configs, and sprites.

The manager constructs exactly those three updater objects, displays `Please wait, checking assets..`, checks/update-runs them, and reports updater-specific failures.

`AssetVersion` parses remote `versions.txt` and local `versions.dat` named double entries. Its network-failure UI installs R336 `AssetVersionHyperlinkListener`, providing a direct family join.

R353 is non-canonical semantic research only.
