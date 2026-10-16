# Cache R228 — Windows path alias integrity

**Lane B only**, relative to private v309 cache R227. This version label is independent of Chat A's full-client R235 and original-bytecode source-recovery versions. Shared coordination [issue #1117](https://github.com/Trexzo/SpawnPK-Client/issues/1117).

## Verified defect and change

`CacheUpdateTransaction.java` derived the OS file-lock name and scoped recovery workspace name using `SHA-256(root.toString())`. On ordinary Windows case-insensitive filesystems, `C:\\...\\assetCache` and `c:\\...\\ASSETCACHE` refer to the **same real directory** but produced **different lock files and workspace prefixes**. A second client could bypass the first updater's lock; crash recovery under a different spelling could miss the existing journal.

R228 derives the lock/workspace identity from a case-folded absolute normalized root **on Windows only**, compares journal ownership case-insensitively there, and conservatively discovers valid pre-R228 scoped journals that were named from a different capitalization. On Linux the original case-sensitive behavior is unchanged.

Public original-independent Java helper is `tools/java/r228/CacheUpdateTransaction.java`. Exact Git blob SHA `d2b4167de17d498bcc443f400d89b24716c9e3a5` was independently verified equal to the **actual private v309 production source's** Git blob SHA. No proprietary original-decompiled Java or non-game libs committed.

## Measured verification

- Private exact base R227 full ZIP SHA-256: `cd20bcd1f0af5d0b6fa3d6b46643c50a7b3625aabe9e50baac5957e9f9d4f939`.
- Source file preimage `CacheUpdateTransaction.java` SHA-256 `4b5234d09c74b491eaba18bfd2fb3ce70b736797154667cd5839299a62393311`; R228 postimage `198bd550540a5b9a2b52c3830be1e9178228f8b02b2a11a038d083516b8d99be`.
- Clean `javac --release 11` on **all 1,277 actual private client Java source files**, **1,388 project classfiles**, **zero compiler errors**. Other 1,276 source files and other 1,387 project classfiles byte-identical to R227.
- **15/15 offline test programs on Linux** passed; the R228 case-insensitive test explicitly skips its Windows-specific assertions there.
- **GitHub Actions Windows Java 11** ran two actual JVM processes, shared-directory mixed-case alias, lock contention, forced `Runtime.halt(17)` mid-transaction, recovery under alternate capitalization, and a simulated legacy journal named from the pre-R228 mixed-case hash: `R228_WINDOWS_CASE_ALIAS_PASS checks=17`.
- **GitHub Actions Ubuntu Java 11** compiled the same exact production helper and test and reported the non-applicable Windows branch as skipped, not fake Linux case-insensitivity.
- Dedicated GitHub Actions run: [38962896523](https://github.com/Trexzo/SpawnPK-Client/actions/runs/38962896523), **both Windows and Ubuntu jobs succeeded**.
- The original-decompiled v309 full client itself was **not** compiled in public CI or launched as a native Windows game.

## Private delivery and Lane A overlay

- Complete private ZIP `SpawnPK_v309_R228_WINDOWS_ROOT_IDENTITY_PRIVATE.zip` SHA-256 **`6a4e0122ac10f08f43dcab6b5f4a89342ee47feb3bf2e4a450a6867ee915709d`**.
- Internal changed-only ZIP SHA-256 `12e2636c4d5905aee0d3a87e712162ef7188cd58af03ea46df8d7acb9485e851`.
- Complete private source ZIP SHA-256 `33d0f0bc3b47d32434c0c5fb79dccca5325df7cc5073106f639a0a25ca7731f2`.
- Rebuilt Java11 production class-only JAR SHA-256 `0836d7de98228622a76143dcf102b434d4169665edb0115655f4ae81f1016fca`.
- Private package contains exact source, compiled JAR, pinned non-game compile/runtime libs, `R228_CHANGED_ONLY.zip` with R227 backup, `R228_Apply_CheckedOverlay.ps1` refusing unknown source hashes, isolated Windows rebuild and 15-test replay scripts, manifest and logs.

**Lane A's canonical R235 source should first reconcile any missing cache R226/R227 overlays.** Apply only this exact `CacheUpdateTransaction.java` after its preimage is SHA-verified as private R227; do not overwrite Lane A's `CacheUpdater.java`, shared downloader, login/GUI, assets or launcher. Rebuild the complete integrated source and independently run Windows real-client acceptance.

## Unverified or remaining risks

- Windows directories configured as **case-sensitive** may contain two distinct directories whose names differ only by case. R228's root identity intentionally assumes the ordinary case-insensitive Windows configuration. Do not enable this on such folders without additional adaptation.
- 8.3 short-name aliases are not canonicalized. Different-version clients still using old lock hashing may bypass the R228 lock. Older legacy journals **without a valid marker** cannot always be attributed to a root by spelling alone.
- There is no proof of power-failure durability, immunity to outside writers ignoring locking, actual private Windows gameplay/graphics acceptance or original obfuscated-bytecode equality.

**Keep PR draft** until integrated full-source Windows testing and lineage reconciliation are done.