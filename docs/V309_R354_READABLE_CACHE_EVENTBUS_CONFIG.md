# R354 — readable v309 Java source pass 3: event bus, cache and config

**Repository:** `Trexzo/SpawnPK-Client`. This milestone advances the owner-private **complete 1,277-file R315 Java source tree**, building on R353 (#1146). This is **readable inferred source**, not original-author identifiers and not an independently certified original-JAR runtime equivalence.

## Actual, source-grounded semantic name candidates

| Previous identifier | New inferred readable identifier | Evidence from Java |
| --- | --- | --- |
| `rs.eventbus.Class87` | `EventBusSubscriber` | Holds subscriber target, reflected method, priority and consumer; `toString()` uses `EventBus.Subscriber(...)`; `EventBus` registers/invokes instances |
| `rs.cache.osrs.util.Class49` | `IndexedCacheFileReader` | Opens main `.dat` and lazily created `.idxN` files via `RandomAccessFile`, reads an `IndexStore`, optional `GZIPInputStream` |
| `rs.cache.osrs.util.Class47` | `MapDependencyRecord` | Three-field dependency object ID, referenced resource and status; produced/collected by `OsrsMapDependencyScanner` |
| `rs.cache.osrs.util.Class48` | `LandscapePlacementVisitor` | Four-integer callback invoked by packed-landscape `readBigSmart`/`readUShortSmart` object/location/type/orientation parser |
| `rs.config.Class50` | `ConfigElementDescriptor` | Shared `key()`, `name()`, `position()` interface implemented by `ConfigItemDescriptor` and `ConfigSectionDescriptor` |

Also renamed the `MapDependencyRecord` fields `field370` / `field371` / `field372` to `dependencyObjectId` / `dependencyReference` / `dependencyStatus`, the `IndexedCacheFileReader` fields `field373` through `field376` to `dataFile`, `cacheDirectory`, `cacheBaseName`, `indexFiles`, and its `method2942(int,int,boolean)` to `readIndexedFile(int,int,boolean)`.

**Safety**: No packets, game opcodes, logic, return types, error handling, or runtime cache data changed. Each symbol has a fixed owner declaration and exact expected reference count / file list; unexpected old symbol references cause refusal. Exact inverse of all 13 symbol renames restored **1,277/1,277 previous source files byte-for-byte**. No transformation is considered a verified original-author name; Java reflection or original-JAR remap parity is not tested.

## Measured real private source and complete rebuild

Input: `SpawnPK-v309-R315-Readable-Deobf-Pass2-Source.zip` SHA-256 `3d9daeb81c1367edc7a2e843a71638d22835bd485bc2d4c09eb0aa43d01b5f22`. The source ZIP contains **1,277** Java files.

- **5** inferred type names, **7** fields and **1** method renamed; **92** identifier replacements.
- **10** unique logical Java compilation units affected (5 renamed owner files); 15 source paths differ when counting both removed/added filenames.
- Numeric `Class<number>.java` filenames: **303 → 298**.
- Files still containing numeric `field<number>` symbols: **894 → 892**.
- Files still containing numeric `method<number>` symbols: **809 → 808**.
- Real Java compilation: installed JDK **21.0.12.1**, `javac --release 11 -proc:none -g:none` **exit 0**, **1,386 compiled classfiles**. The two dependencies contain **zero `rs/` game classfiles**; no original project binary fallback.
- Candidate compiled JAR SHA-256 `47900804e621ff2d583cec35f6d25691630067405b8f6c3bcedfba9e17f0e3a6`.
- The **entire private build kit** was repackaged with the new 1,277 source SHA manifest, extracted into a **different fresh workspace**, and built again: exit 0, 1,386 classes, **the same exact JAR SHA-256**.

Private deliverables:

| File | SHA-256 | Notes |
| --- | --- | --- |
| `SpawnPK-v309-R315-Readable-Deobf-Pass3-Source.zip` | `e515f96d753a8e0458c21b7a4ebf16c080411ea3ddbf85d184022497bfffd768` | 1,277 Java source files; R354 naming and digest manifest |
| `SpawnPK-v309-R354-Readable-Pass3-Reproducible-Build-Kit.zip` | `a711458af69c21a8be7ab4f89ed4cd70629430fe0aee2117664240b48a0e44bd` | All Java, two pinned non-project dependencies, offline build tool |
| `SpawnPK-v309-R354-Readable-Pass3-Receipt.json` | Mutable summary of tested source hashes and independent rebuild | Full per-source SHA-256 and inverse proof |

## Reproducible private refactor

The committed `scripts/prepare_v309_r354_readable_subsystems.py` requires the exact private R353 source ZIP SHA, all 1,277 Java files, and the five original class owners' exact SHA-256. It refuses source member traversal/symlink/casefold issues, unexpected symbol owners or counts and existing output destinations. It writes an entirely **new private** R354 source ZIP. Each transformation is reversed in memory, and any byte drift fails closed.

```powershell
py -3 scripts/prepare_v309_r354_readable_subsystems.py `
  --r353-private-source-zip "C:\private\SpawnPK-v309-R315-Readable-Deobf-Pass2-Source.zip" `
  --new-private-source-zip "C:\private\SpawnPK-v309-R354-Readable-Source.zip"
```

**GitHub CI is synthetic-only**, using small fake Java classes. Proprietary/reconstructed complete source, private dependency JARs and compiled candidate JARs are not committed to this public repository or distributed by GitHub Actions.

## Next source milestone

Continue prioritizing high-confidence named class groups, then the far larger method/field naming surface, with source-level safety checks, exact inverse, zero-project-class clean compilation and independently checked original-JAR method semantics before promotion. The existing Source-M1 certification gates remain applicable.

**Production v312, updater, original v309 JAR, cache and live service remain untouched.** Keep this PR draft/unmerged.
