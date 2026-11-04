# R356 — SpawnPK v309 full-source readability pass 5

**Correct source-reconstruction repository:** `Trexzo/SpawnPK-Client`; stacked on R355 PR #1148. This change does **not** modify the production v312 launcher, updater, original v309 JAR, assets or live servers.

## Exact private source inputs

Base: owner-private R355 1,277-file readable source archive `SpawnPK-v309-R315-Readable-Deobf-Pass4-Source.zip`, SHA-256:

`7b58b0cc0292aa1a573ff2d1b940eb92fbbb0c7676b9cfdb4931b6824d00ad2c`

This source is **reconstructed/edited candidate Java**, not recovered original-author text. Each file is independently verified against the ZIP's `PRIVATE_R355_READABILITY_MANIFEST.json` and the complete archive hash. No raw private Java or compiled game JAR is placed in this public PR.

## Concrete readability improvements

The recovered Java and its callers justify these seven **inferred class names**:

| Obfuscated class | Inferred readable name | Actual source evidence |
| --- | --- | --- |
| `rs.util.Class74` | `ItemIconCacheLoader` | Guava `CacheLoader` subclass used by `AssetIconManager` for item-sprite keys |
| `rs.util.Class75` | `SpriteIconCacheLoader` | Companion cache loader for sprite directory + size |
| `rs.util.Class76` | `ItemIconCacheKey` | Immutable item ID, item quantity and size; `toString()` explicitly says `AssetIconManager.ItemKey(...)` |
| `rs.util.Class77` | `SpriteIconCacheKey` | Immutable icon directory and size; `toString()` explicitly says `AssetIconManager.SpriteKey(...)` |
| `rs.plugins.devtools.Class272` | `DevToolsWidgetDisplay` | Text, screen X/Y, `WidgetType` value object; `toString()` says `DevToolsWidgetOverlay.WidgetDisplay(...)` |
| `rs.plugins.notifications.Class275` | `NotificationSoundMode` | Enum `NATIVE`/`OFF` returned by `notificationSound()` config and consumed by notification mode switch |
| `rs.util.Class82` | `MacOSUiSupport` | macOS native fullscreen, dock attention and foreground focus methods called by UI/tray code |

Also renamed **13 fields**: asset-icon cache manager references, item ID/quantity/size, sprite directory/size, DevTools display text/X/Y/type, notification label and macOS logger. Renamed **13 methods**: item/sprite key accessors, DevTools display accessors, notification enum label accessor and macOS UI actions.

These are **33 symbols**, **178 exact identifier replacements across 22 Java source files**, with seven renamed owner paths. The edit plan is pinned to the exact input source hashes and expected symbol counts. No packet IDs, method bodies, branch conditions or game logic were intentionally changed.

### Exact reversible proof

The edit process records output positions of each changed identifier. The inverse is applied in reverse operation order, so pre-existing names in unrelated strings and the independently meaningful `toString()` literals survive intact. The complete **1,277-file R355 source tree** was reconstructed byte-for-byte in the inverse check.

Names remain `INFERRED_CANDIDATES`; original-author identifiers, reflective name access, and original-v309 JAR bytecode parity **have not** been independently certified.

## Full Java clean rebuild — actual local verification

- Entire post-rename **1,277 Java-file tree** compiled with installed JDK 21 targeting Java 11: `javac --release 11 -proc:none -g:none`, UTF-8, explicit empty sourcepath.
- **Exit 0**, **1,386 compiled classfiles**.
- Two SHA-pinned dependency JARs contain **zero `rs/` game classfiles** — no original game-class binary fallback.
- Deterministically packed source-built client candidate JAR SHA-256: `31ca1fc3e690d51544a4993a1daa700f1a528d914cd95af9b4947db8c7a1ed23`.
- A self-contained private build kit was independently extracted into a new temporary directory; executing its own `tools/rebuild_from_source.py` reproduced **exit 0, 1,386 classes, and the identical JAR SHA-256**.

### Private artifacts prepared for the owner

| Artifact | SHA-256 |
| --- | --- |
| `SpawnPK-v309-R356-Readable-Deobf-Pass5-Source.zip` | `e0fd993155ff4842ff35afa10e9dc77d47832e707b70f3dbac23427b9f423aa7` |
| `SpawnPK-v309-R356-Readable-Pass5-Reproducible-Build-Kit.zip` | `dbcc513c8cc14143a7859e07b8a49ddb9efa294e349b1c0ff523efc3cdc4f6c2` |

The downloadable ZIPs are **private candidate artifacts**, not GitHub Source-M1 publications.

## Reproducibility in the correct repository

`scripts/prepare_v309_r356_readable_asset_helpers.py` consumes the R355 exact owner-private ZIP and writes only a new private source ZIP. It validates exact archive SHA, all 1,277 inner Java SHA-256 pins, safe ZIP paths, the seven original class-owner SHA-256 values, symbol counts, file counts and inverse reconstruction. It refuses overwriting the output.

```powershell
py -3 scripts/prepare_v309_r356_readable_asset_helpers.py `
  --r355-private-source "C:\private\SpawnPK-v309-R315-Readable-Deobf-Pass4-Source.zip" `
  --new-private-source "C:\private\SpawnPK-v309-R356-Readable-Source.zip"
```

Public CI uses **synthetic Java snippets only**: it tests declaration and owner SHA mismatch, unexpected source references, output path collisions, byte-exact reversal and preservation of pre-existing descriptive strings. Hosted CI does not compile the real private source or certify original-JAR runtime semantics.

## Deobfuscation frontier

After Pass 5, of the initial 307 `Class<number>.java` filenames, **286 remain** (21 renamed across five passes). **883** Java files still contain `field<number>` identifiers and **806** still contain `method<number>` identifiers. These are lexical scope counts, not a percentage of full semantic equivalence.

The next priority is naming the larger remaining source graph with careful reference mapping, plus original-JAR bytecode and reflection checks before any Source-M1 publication. Keep this PR **draft and unmerged**.
