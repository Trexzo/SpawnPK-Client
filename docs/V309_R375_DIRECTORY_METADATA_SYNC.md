# R375 — advisory parent-directory metadata sync (private recovered v309 candidate)

**Repository:** `Trexzo/SpawnPK-Client` · **Base:** R374 PR #1169 · **Release gate:** CLOSED, draft and unmerged.

## Source-grounded finding

R374 atomically staged rename receipts and forced the data bytes before publication, but did not explicitly attempt to sync parent-directory entries after the `Files.move`, `Files.createFile`, or `Files.delete` metadata operations. A file-content flush alone cannot establish directory-entry persistence after power loss.

## R375 bounded private change

Only `rs/gui/loadouts/io/LoadoutStore.java` changed among 1,277 recovered Java source files. `tryForceParentDirectory(Path)` checks that the parent is a real directory with `NOFOLLOW_LINKS`, then attempts `FileChannel.open(parent, READ).force(true)` on providers that allow it. It returns false and emits a warning on unsupported / inaccessible providers. This is **best-effort**, not a release gate and not a guarantee. R375 adds attempts after publishing/deleting rename and version receipts, replacing the folder and order files, updating version markers, and removing old rename data and sidecars. The previous SHA/lock/receipt checks remain in place.

## Source-backed verification

- Full private `javac --release 11` compilation of **1,277** Java sources yields **1,388** classfiles; clean rebuilt JAR SHA-256 `f8aae54c7b5d262fa994783c161b19fd3387b30130432f78a005ac697d54c5ca`.
- **24** new source-backed scratch-directory assertions: provider probe succeeds on the test Linux filesystem; a regular-file parent path refuses sync; successful rename order reconciles and consumes receipt; interrupted precommit preserves original; malformed/orphaned receipts never delete the original.
- **310** inherited Java persistence/serializer assertions PASS (R374=32, R373=45, R372=56, R371=16, R370=29, order=28, store=44, serializer=60).
- Independent, fresh-extraction rebuild reproduces the exact same 1,388-class JAR SHA-256 and re-runs the R375 source-backed test.
- R374 input archive SHA: `a8c7b3a044ce1ac106069bd935412edbaabff4546e3618df5810e54ccf924795`; R375 candidate SHA is in the witness. Each file and SHA manifest is checked, and only one source changed.

## Critical limits

This test uses the Linux filesystem in a scratch directory and is **not** a physical power cut, crash/power-failure simulation, Windows filesystem acceptance, parent-directory durability proof, or complete multi-file transaction. Windows and other providers may not support Java directory forcing; such failures log a warning but do not stop a recovery operation. The last fingerprint-check/rename race remains possible with noncooperative writers.

No original v309 binary parity, actual client GUI/login, real user-cache migration, v312 integration or production deployment is claimed. **Keep private source, draft PR, unmerged and no updater changes.** Hosted CI contains only the source-archive integrity verifier and synthetic micro-archives: it does not compile or upload private Java.
