# SpawnPK v309 R312 — offline renderer and empty-scene runtime acceptance

**26 October 2026 — validation-only milestone on the complete, owner-private recovered v309 source tree.** Exact-v311 original-bytecode recovery is a different project.

## Verified source/client identity

- 1,277 privately held recovered Java sources, with per-file SHA-256s checked against the private R311 manifest.
- 1,386 original-name compiled client classfiles, rebuilt from all 1,277 Java sources using Java 11 target.
- **Zero production Java changes since R311.** The R312 JAR is bit-for-bit the previously accepted R311 JAR.
- Pinned class-only JAR SHA-256: `b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721`.

## New R312 acceptance work (REAL compiled client code, isolated test fixtures)

A single owner-private Java test compiles against the actual recovered game JAR and exercises:

1. **576 software triangle raster frames:** 192 frames each at 765×503, 640×480 and 1400×900. Real `Rasterizer3D.method2368` draws into actual `Rasterizer2D` framebuffers, using a deterministic synthetic palette. For 640×480, exactly **17 collinear triangles** have zero area and correctly draw zero colored pixels; the test derives the signed area before asserting raster coverage.
2. **600 empty-scene rendering frames:** the real `Scene.drawScene` and `Scene.setViewport` code run with an in-memory, asset-free 4-plane scene and visibility-radius transitions **25 → 50 → 25**. The test checks actual visibility grid dimensions at every frame; it does **not** claim the empty scene displays a rendered game world.
3. A **constructor-free, inert Launcher/Client test fixture** avoids UI initialization, sockets, cache access, real accounts and device/OS identifiers. It is for offline acceptance **only**, not shipped as modified production client code.

**R312 new assertions: 2,357/2,357 PASS.** Prior real compiled-client tests rerun from the same archive: R308 256, R309 38, R310 15 and R311 37 = **346/346**. **Combined 2,703/2,703 PASS** with all test process exit codes zero.

## Fresh owner-private archive replay

Private file name: `SpawnPK-v309-R312-Full-Recovered-Source-Private.zip`. Size **22,218,095 bytes**. SHA-256 **`1d01d43a184fb187c287abd53b995e7abbd61889a501d3f6e26f524bb475b6e3`**. It includes all 1,277 private Java files, two pinned dependency JARs, unchanged compiled class-only JAR, five private real-client Java regression sources, strict Python acceptance/rebuild tooling, logs and full source/dependency manifest. **Archive is owner-private, NOT uploaded to GitHub.**

From a fresh extraction, the owner-private commands `python tools/run_r312_offline_acceptance.py` and `python tools/rebuild_from_source.py --output r312_rebuilt.jar --javac javac` both completed successfully. The new jar SHA exactly matches the pinned R311 JAR. Invalid source/dependency/test preimages are rejected before running the acceptance suite.

## What R312 does not prove

**NOT VERIFIED:** an authenticated real-server session, the native Windows client UI or GPU backend, authentic cache/texture-backed world or GUI rendering, gameplay interaction, a sustained real session, or device/hardware integration. No original 10,772-file cache bundle, original `config.bin`, account data, credentials, or actual gameplay server traffic were used. The fact that the rasterizer produces synthetic framebuffer pixels **does not establish that an asset-backed SpawnPK world renders correctly**.

This release is an improved offline runtime acceptance **harness**, not a new gameplay-code release. Keep [Draft PR #1143](https://github.com/Trexzo/SpawnPK-Client/pull/1143) unmerged, preserve R311 as the exact production baseline, and coordinate the next asset-backed GUI/local-session acceptance through [issue #1117](https://github.com/Trexzo/SpawnPK-Client/issues/1117).
