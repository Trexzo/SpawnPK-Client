# SpawnPK v309 R308 — scene placement bounds and private release

**20 October 2026.** Sole active [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) remains **DRAFT**, with no installed owner changes, public private-client binaries, or merge into `main`.

## Actual production change

The previous R307 `Scene.method1909` indexed the scene grid on an invalid plane (`-1`) before checking bounds, producing a real `ArrayIndexOutOfBoundsException`. R308 applies the existing `isSceneTileInBounds(plane,x,y)` helper **before any mutation** in eight real public scene placement entry points:

`method1909`, `method1890`, `method2219`, `method3074`, `addGroundDecoration`, `method1657`, `method1680`, and `method3442`.

Each method's own plane/X/Y argument ordering is preserved. The real-client regression checks rejection of out-of-scene planes and coordinates without a changed tile, plus successful in-bounds terrain, walls, decoration and item pile placement. No model definitions, cache data, packet opcodes, networking or other original Java class changed.

Original `rs/Scene.java` R307 SHA256 **`2ed273e3dd162a5b1884f776dfcec2460f49b732ea0206b6211aeca72b3ef092`** → R308 source SHA256 **`baa165aacae5d9408c21235bef656ab459b41e666906991ea49ed4622d23aeae`**.

## Independent owner-private rebuild and regression

The exact original R278 archive SHA256 **`e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280`** and R265 SHA256 **`9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb`** were verified. The public R302–R307 SHA-pinned rebuild chain was independently restored from the preceding verified private releases.

**Two full original Java 11-target builds** independently compiled **1,277 Java sources → 1,386 classes** and produced byte-identical class-only R308 JAR SHA256:

```
501072d504a4e03a758f44aaa32f0990d3f1599662f6f6d2fa0d83a14e6fc314
```

A direct per-class binary comparison to R307 showed **only `rs/Scene.class` changed; 1,385 classes are byte-identical**, with no added or removed classes.

The actual compiled R308 client passed the **256/256** new placement assertions, plus all **13 previous** compiled-client test programs, including the R305 viewport reference oracle (**102,510 samples, zero mismatches**), earlier scene-boundary suites, R306 radius transition, and R307 cold/GPU visibility. Total reported genuine Java assertions/reference comparisons **106,769/106,769 PASS** across 14 test programs, each with process exit 0. These were independently rerun under Linux/Xvfb with the genuine client and its pinned private dependencies; R307 cold and GPU entry-point tests passed as well.

## Fresh R308 graphical replay

A fresh **isolated** original-cache test home staged all **10,772 authentic owner cache files** (209,747,201 uncompressed bytes) and a SHA-verified R308 class JAR. The original, bounded R285 Java AWT Robot and 127.0.0.1 synthetic game server then ran the actual R308 client at **1400×900 Linux/Xvfb**.

**Outer process exit 0**, client GUI PASS, actual rendered region **13386 / field1134**, viewport nonblack ratio **98.493%**. The Robot selected **Cook** on range **114**, and the isolated server received the actual ISAAC-decoded outgoing **opcode132, length 6, world tile (3362,4769)**, followed by matched synthetic incoming **opcode253** acknowledgment. New R308 **52-byte** received wire SHA256 **`651dadfae3be480e3253157321c720b5fd222366a08e43c5b0491500e4cf498b`**. Client, server and Robot processes cleaned up. Original cache files are **not included** in the release.

## GitHub source-safe artifacts

- `tools/recovery/r308/rebuild_r308_from_pinned.py` — exact tested public rebuild, Git blob **`46be4e8e32f1f0827ba1a3356c9d607f212c2080`**, locks original parent builder and expected source and output JAR hashes, refuses occupied output.
- `tests/java/r308/R308ScenePlacementBoundaryRegression.java` — exact executed real-client regression, Git blob **`b354a58272b3a32c18da93330260b63a68e69384`**.
- `tests/python/r308/R308SourceSafetyRegression.py` — **18/18 source-only tests** included in both Ubuntu 24.04 and Windows Server 2022 GitHub Actions CI, success on both platforms.
- [Windows/Linux source-safety CI run](https://github.com/Trexzo/SpawnPK-Client/actions/runs/39441245854) and [Recovery CI](https://github.com/Trexzo/SpawnPK-Client/actions/runs/39441245683) both successful. These hosted jobs do **not** have the private JAR/cache and do not prove native Windows gameplay.

## Private owner-only release

`SpawnPK_v309_R308_SCENE_PLACEMENT_BOUNDS_PRIVATE.zip`, **3,188,845 bytes**, SHA256 **`977645c2ed90c0936815e9da5ca609ee23480176088137f8d3e7ee3b88654d6c`**. **24 entries**, two independently built byte-identical deterministic ZIPs, and independent verifier **77/77 PASS** (CRC, per-member SHA/size, 1,386-class private JAR, exact class diff, 14 Java process exits, fresh screenshot dimensions, decoded localhost packet/reply and explicit acceptance limitations). Contains only the class-only rebuilt private JAR, authored reproducibility/test scripts and fresh private evidence; **no original complete game executable, full recovered source tree, original cache, fonts or credentials**. Do not publicly upload this ZIP or original rendered screenshots.

**Still NOT TESTED:** owner-native Windows R308 graphical and GPU mode (including extended 50-tile visual rendering); real authenticated production game server, cooking item creation/inventory and sustained gameplay. Existing R297 native runner is pinned to old R295 and cannot accept R308. Keep PR #1142 draft and owner-installed files unchanged; native Windows R308 acceptance is the next major validation milestone.
