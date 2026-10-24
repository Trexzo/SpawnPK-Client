# SpawnPK v309 R308 — scene placement boundary authority

**20 October 2026.** Genuine recovered-client source defect reproduced and fixed in one Java class. PR #1142 remains DRAFT. No original game archive, complete recovered Java source, cache, fonts or credentials are published to GitHub or installed on the owner PC.

## Reproduced failure and correction

The genuine R307 compiled client threw `ArrayIndexOutOfBoundsException: Index -1 out of bounds for length 4` from `Scene.method1909` when handed invalid plane -1. Its public scene-placement siblings could likewise index `this.tiles[plane][x][y]` before range validation.

R308 adds a pre-index early-return guard using the existing `isSceneTileInBounds` helper to exactly eight placement entrypoints: `method1909`, `method1890`, `method2219`, `method3074`, `addGroundDecoration`, `method1657`, `method1680`, and `method3442`. Each guard uses the actual method-specific plane/X/Y argument ordering. No scene renderer, object models, packets, cache resources or network endpoints changed. Valid tile inserts remain intact.

Original R307 Scene.java SHA256 **`2ed273e3dd162a5b1884f776dfcec2460f49b732ea0206b6211aeca72b3ef092`**; R308 postimage SHA256 **`baa165aacae5d9408c21235bef656ab459b41e666906991ea49ed4622d23aeae`**.

## Real private source build and regression

Exact owner-held private R278/R265 inputs were SHA-pinned. **1,277 actual Java files** compiled to **1,386 Java 11-target classes** in three independent complete builds, including one invoked using the public pinned R308 recipe. All three produced the same class-only JAR SHA256 **`501072d504a4e03a758f44aaa32f0990d3f1599662f6f6d2fa0d83a14e6fc314`**.

Independent per-class JAR comparison with the actual R307 binary: only **`rs/Scene.class` changed**; other **1,385 classes** byte-identical.

The new original-class R308 placement test reproduces a **RED R307 exception** in `method1909(-1,...)` and passes **256/256** checks on R308 (8 entrypoints, invalid extreme plane/X/Y, and authentic valid tile placement). Every existing R293–R307 compiled Java suite also passes on R308, including the R305 independently computed visibility oracle **102,510/102,510, zero mismatches**, the dynamic radius and GPU/cold start tests, object menu authority and prior scene regressions. **106,769** total authentic-client JVM checks including the new 256.

The public source-only `tests/python/r308/R308SourceSafetyRegression.py` passes **18/18**. The GitHub Windows Server 2022 and Ubuntu 24.04 CI runs these tests with no proprietary game files; CI source-only success is not native Windows gameplay verification.

## Linux graphical compatibility

The exact compiled R308 JAR ran in a disposable Linux/Xvfb test home copied from previously verified authentic owner cache. Outer process **exit code 0**. Original OSRS region **13386 / field1134** rendered at 1400×900. Java Robot selected **Cook** on range object ID **114**, sending ISAAC-decoded outgoing object opcode **132**, six bytes, world **(3362,4769)** to an isolated **127.0.0.1** mock server; the server returned matching synthetic opcode **253** acknowledgment. The actual received socket wire SHA256 was **`7eb11a705a3f810f669de79ebb351a1c60bed8cbef2397dfc2cd60ce2330f9c7`**. Real PNG screenshots and timeline and socket receipt are contained privately. This is Linux synthetic-server graphical compatibility, not a production server or native Windows test.

## Public GitHub source-only outputs

- `tools/recovery/r308/rebuild_r308_from_pinned.py` — SHA-pinned original R307 builder, exact input source/compiled JAR hashes, eight explicitly oriented placement guards, no-overwrite output, fully compiled source; Git blob **`46be4e8e32f1f0827ba1a3356c9d607f212c2080`**, byte-identical to executed builder.
- `tests/java/r308/R308ScenePlacementBoundaryRegression.java` — actual R307 RED / R308 256 GREEN real-client test; Git blob **`b354a58272b3a32c18da93330260b63a68e69384`**.
- `tests/python/r308/R308SourceSafetyRegression.py` — 18 source-only hash/coordinate/negative-path/privacy tests, Git blob **`d11a5d108ffcd50a1d8c2db4eaba0053c780e283`**.
- `.github/workflows/v309-r289-windows-safety.yml` includes R308 in Windows/Linux source-only matrix.

## Owner-private release (not publicly committed)

`SpawnPK_v309_R308_SCENE_PLACEMENT_BOUNDARY_PRIVATE.zip` — **2,819,505 bytes**, SHA256 **`5fcc45b74db8f276ce143ad82d46f79fa19ddf4f03300eec3963e90134b3f868`**, **20 ZIP members**, two byte-identical deterministic ZIP builds. The release verification script passed **73** source, SHA/CRC/manifest/class-count, JVM, GUI and localhost receipt checks. Contains the owner-private class-only R308 JAR, public-safe build and test scripts, R307 failing and R308 passing logs, complete build logs, genuine Linux screenshots, JSON timeline, and 51/52-byte-scale local socket receipt. It excludes the original complete game JAR, full recovered Java source tree, original cache, fonts and credentials. Do not publish this private release, screenshots or classes in public GitHub.

## Acceptance boundary

**Native owner Windows R308 GUI and native GPU rendering NOT TESTED.** The older native owner acceptance launcher R297 is pinned to R295 and cannot verify R308. Original authenticated production-server cooking, inventory effects and sustained gameplay NOT TESTED. Keep PR #1142 DRAFT and preserve the owner's existing installed client and `main`.
