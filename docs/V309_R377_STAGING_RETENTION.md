# R377 — Staging retention metadata, read-only (private v309 candidate)

**Correct repository:** `Trexzo/SpawnPK-Client` · base R376 draft PR #1171.

R376 can list possible staging-file names, but **age alone does not prove a file is orphaned**. The R377 private candidate extends the diagnostic through a private method `inspectStagingRetentionSnapshot(long observedAtMillis)` which reads only filesystem attributes (never file bytes). It uses a bounded set of R376 staging prefixes, does not follow symlinks, and assigns advisory time buckets `UNDER_24H`, `OVER_24H`, `OVER_7D`, or `CLOCK_UNKNOWN`, plus `EMPTY`, `SMALL`, or `LARGE` size buckets. Nonregular entries become `UNSAFE`; entries changing during inspection become `UNAVAILABLE`. Output is deterministically sorted and immutable. **The method is a diagnostic hook, not a new user-facing UI panel.**

No staging files are opened for content inspection, quarantined, renamed, deleted, or classified as safe for deletion. A week-old stage may belong to an active long-running writer, and a newly created stage may be abandoned. The directory listing and later attribute read are not atomic; no cross-process lock ownership is inferred.

## Source-backed private verification

- R376 source archive SHA-256 `030f378e4ba871ef1e7d269e1b1f655f01a82f084df92d650cf78dc7cb25c671` → R377 private source archive, SHA pinned in witness. Exactly **one of 1,277** Java source files changed: `rs/gui/loadouts/io/LoadoutStore.java`.
- New actual-source Java scratch contract **25/25 PASS**, with R376 predecessor contract **23/23 PASS**; other inherited suites **334 assertions PASS** (357 total inherited).
- Full JDK21 `javac --release 11`: **1,277 source files → 1,388 class files**. Initial build and independent clean build-kit extraction reproduce JAR SHA-256 `81cb2e2bd0b1c88e5485ba78be95963054fcc12241e4e2f051b5399a2a23e96d`.
- Public SHA verifier **29 synthetic tests PASS locally**. Public CI runs a generic JDK metadata probe on Windows/Ubuntu. These hosted tests neither compile private source nor run the client.

## Gates

**Draft/unmerged.** No original v309 JAR parity, authenticated login, original GUI runtime, live user cache migration, active-writer detection, Windows private-source execution, actual power-cut test, reliable directory persistence, full multi-file transaction or v312 compatibility. Source publication gate remains **CLOSED**. Original v309 JAR, production v312, signed updater and caches are unchanged. Never treat age or file size as authorization to delete recovery evidence.
