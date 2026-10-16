# Cache R230 — full-ancestry Windows cache root identity

**Lane B** cache-only production helper, based on private cache R229. Coordination issue #1117.

R229 checked only case-only sibling names in the *last* cache-root directory. Under case-sensitive Windows parents, two distinct absolute paths like `Parent/assets` and `parent/assets` can still collide after `toLowerCase(Locale.ROOT)` even though their last components are identical. R230 walks every existing ancestor and tests case-only sibling entries with `Files.isSameFile`; it refuses two physically distinct ancestors that would hash to one lock/journal name, and rechecks after lock acquisition and immediately before promotion.

## Exact private source evidence

- Only modified Java: `src/rs/cache/updater/assets/CacheUpdateTransaction.java`.
- R229 preimage SHA256: `d63b3bde561d8603da743482bb539f5992946bd5b513da747bbc0e47be0fafad`.
- R230 postimage SHA256: `8ee21c114b98f7ece960b1347609edd8ffce300614f19d7f3103baaeaa715882`.
- Public original-independent helper Git blob SHA1: `1947ee99f76a779ea7554ef9ec7ba8727a81295c`, verified byte-identical to the private production helper.
- Actual complete private Java11 target `javac --release 11`: **1,277 Java files, 1,388 classfiles, zero errors**, only CacheUpdateTransaction.class differs from R229.
- All **17 local Linux offline regression programs PASS**, including the new R230 14-check ancestor/path-collision suite, inherited R229 sibling alias tests, crash recovery, multi-JVM locks, downloader and real cache ZIP extractors.
- Public CI exercises only this independent helper, original-independent smoke, and earlier independent Windows alias regression, **not the private full game**.

## SHA-pinned private handoff

Complete `SpawnPK_v309_R230_FULL_ANCESTRY_CACHE_GUARD_PRIVATE.zip` SHA256 `9250ecba1f66c148565baeac7c51fab7e9439d72ec3c84d69ce847f4536a96a4`.
Internal changed-only ZIP SHA256 `93737a8f65e96abc08d5d2735362a3cce8b90ccdd9de751e61f42a3ebaa805fd`.
Full source ZIP SHA256 `1ec544b7410f5164ea9cc5c3e77f12b7f9bf055687cb29972566299a6070b57c`.
Compiled JAR SHA256 `1d5185f2335e1fecdc0a4ba0a817f8179e0b7af4da91ee3dc2f8ef68d65e47e1`.

Overlay ONLY this helper, preserving canonical Lane A's updated `CacheUpdater`, downloader, GUI and launcher; check the approved R229 preimage and back up original first. Source-only JDK11 compile, Windows isolated test scripts and reports are enclosed.

## Remaining limits

The directory case mode, outside file writers, DOS 8.3 names, UNC aliases and concurrently running older clients remain potential limitations. This is not a race-free handle pin, not private Windows gameplay or successful authenticated login. **Keep draft** until integrated source and native runtime acceptance.
