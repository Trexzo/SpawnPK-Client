# R222 — Cache-root scoped recovery and strict journal validation

Lane B only. This is a follow-up to the private R221 crash-safe cache transaction, **not** a new full-client source recovery or the original-obfuscated-code R222.

## New production behavior

- New temporary cache transactions use `.spk-cache-update-<24-hex-root-hash>-<random>` instead of a global unscoped prefix.
- The recovery scan skips workspaces belonging to other R222 cache roots **before examining their journal or backups**.
- Existing R221 legacy transaction names remain readable and conservatively fail closed on unidentified backups.
- Every ancestor of the configured cache parent is checked using NOFOLLOW attributes; symlinks and unusual filesystem objects are rejected.
- Journals require a valid phase and exact record layout. Journal writes drain the complete ByteBuffer before forcing and swapping the marker.
- No production code outside `CacheUpdateTransaction.java` was changed relative to the private R221 candidate. The upstream `CacheUpdater.java` remains byte-identical.

## Private full-source acceptance

- Exact R221 input bundle SHA256: `eaa8d7e9f4ab21466a3dee462ed8fa74f6271dbf12cd178c2b110ce802b673d9`
- R222 full private source build: **1,277 Java sources**, **1,386 JVM classfiles**, `javac --release 11`, **zero compiler errors**
- New true R222 recovery-isolation tests: **8 cases passed**, including malformed foreign workspace, unmarked foreign backup, independent root recovery, corrupt own journal preserving original files, link ancestor and separate successful installs
- Inherited R221 crash/lock regression **10/10**, R220 cache transaction regression **8/8**, plus 6 other offline suites passed
- SHA256 R222 production helper: `726262c28ca7d5f1bc1b466b805dbfdb45ef541cbdf479de1e3dd9e5e52968e6`
- SHA256 unchanged CacheUpdater: `a7276eee8c1e179de9cef9c1a13b77050435057d13c9f87c0caac9a97360a396`
- Full private R222 bundle SHA256: `56a98dff3ff2bbe37b0c7e7c8cc1e2685b688d12983c1b96feeed5d7a718a488`
- Changed-only ZIP **inside** private bundle SHA256: `d63eec883e13257f0264499b942998f74f42ddf4f429934960c08388ed0b79e3`

Public GitHub contains only this original-independent newly written Java class, synthetic smoke regression and workflow; the private v309 Java owners, dependency JARs and original resources are **not** published.

## Ownership and integration

Coordination: [#1117](https://github.com/Trexzo/SpawnPK-Client/issues/1117). Lane A (#1084) owns integrated R225+ runtime, Windows resource/GUI checks and package acceptances. Lane B owns cache transactions and safety. Use the `r221-to-r222` overlay if already on R221 or `r220-to-r222` if directly on R220, with manifest SHA preflight. Neither overlay can be blindly placed over Lane A's different R225 `CacheUpdater.java` without a conflict review.

**Remaining risks:** actual private Windows client/regression tests, Windows filesystem sharing and junction behavior, unexpected third-party cache mutators that disregard the lock, preexisting legacy anonymous backups, real power-loss durability, complete GUI/gameplay and original JVM Code parity. No live game endpoint was used. Keep DRAFT.