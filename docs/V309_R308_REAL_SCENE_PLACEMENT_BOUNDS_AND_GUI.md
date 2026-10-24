# SpawnPK v309 R308 — real scene placement boundary authority

**20 October 2026.** Recovered-source production fix, actual compiled-client red/green regression, four byte-identical complete Java 11 builds, and authentic-cache Linux GUI smoke test. Sole-active PR #1142 remains **DRAFT**; `main` and owner-installed clients unchanged. Private client binaries, original cache and original recovered Java source are not committed to public GitHub.

## Actual reproduced R307 defect

The genuine R307 `Scene.method1909(-1,50,50,...)` throws `ArrayIndexOutOfBoundsException: Index -1 out of bounds for length 4`, because the terrain-placement path indexes `this.tiles[plane][x][y]` before checking its scene plane. Seven sibling public terrain/object/wall/decoration writers had the same unchecked-coordinate structure, despite the separately protected interactive-object builders.

The production change introduces **no new data structure or opcode**. It reuses the existing source-owned `isSceneTileInBounds(plane,x,y)` and returns before allocating a tile or changing a scene object when the location is invalid. Explicit original argument orientation is preserved:

| Public scene writer | Plane, X, Y original variables |
| --- | --- |
| `method1909` — terrain | `var1,var2,var3` |
| `method1890` — ground object | `var1,var7,var3` |
| `method2219` — wall | `var10,var6,var4` |
| `method3074` — wall decoration | `var4,var8,var2` |
| `addGroundDecoration` — ground decoration | `var1,var7,var3` |
| `method1657` — item pile | `var7,var1,var8` |
| `method1680` — alternative wall | `var10,var6,var4` |
| `method3442` — alternative wall decoration | `var4,var8,var2` |

In-bounds behavior, object content, and prior R290–R307 scene, renderer, client protocol and GPU-viewport fixes are unchanged.

**Actual Scene.java SHA256:** R307 preimage `2ed273e3dd162a5b1884f776dfcec2460f49b732ea0206b6211aeca72b3ef092` → R308 postimage `baa165aacae5d9408c21235bef656ab459b41e666906991ea49ed4622d23aeae`.

## Compiled real-client regression and build proof

- Original **R307 JAR RED**, reproduced in `R308ScenePlacementBoundaryRegression`: `R308_SCENE_PLACEMENT_BOUNDARY_CRASH method=0 plane=-1 x=50 y=50`. The test uses a real original `Class11` instance, without fake production classes or original model-assets initialization.
- Exact **R308 JAR GREEN 256/256 assertions**: all eight actual public methods, four extreme invalid values at each of plane/X/Y, plus four valid positions per method, checking untouched scene state for invalid updates and actual stored terrain/wall/decorative/item-pile objects on valid tiles.
- **All previous authentic R293–R307 Java regressions PASS**, including the independent R305 visibility reference oracle **102,510/102,510 with zero mismatches**, R306 dynamic radius tests and R307 cold-start/GPU alignment tests. Combined original Java checks and new R308 regression: **106,769 successful assertions/comparisons**.
- **Four byte-identical complete private builds**, using the original SHA-pinned owner R278 and R265 source inputs and filtered original Java dependency path: **1,277 original Java files → 1,386 Java 11-target compiled classes**. The fourth build was performed by the exact public source-safe R308 recipe, not by supplying a patched `Scene.java`. Resulting class-only JAR SHA256 **`501072d504a4e03a758f44aaa32f0990d3f1599662f6f6d2fa0d83a14e6fc314`**.
- Binary per-class comparison with original R307 JAR: only **`rs/Scene.class` changed**, all **1,385 other classes byte-identical**.
- Public exact `tools/recovery/r308/rebuild_r308_from_pinned.py` Git blob **`63dd69ed76a02bb6738272746f75fbd4ce873c50`**, identical to the fourth compiled build recipe. It imports the original public R307 builder only after exact SHA256 verification, patches the original exact recovered R307 scene source with eight anchored modifications, enforces new source and compiled-JAR hashes, preserves 1,277/1,386 counts, refuses existing output, and corrects immediate R307→R308 source provenance in its generated manifest.

## Authentic Linux GUI smoke test

Real R308 compiled class-only client ran using a disposable copy of the previously SHA-verified original owner cache (10,772 assets). In Linux/Xvfb at **1400×900**, the original rendered OSRS region **13386 / field1134** populated the 3D world; Java Robot selected **Cook** on range object ID **114**. The isolated localhost synthetic server received an ISAAC-decoded outgoing object action **opcode132, six bytes, tile(3362,4769)** and returned paired synthetic **opcode253** acknowledgment. Genuine **52-byte** captured wire SHA256 **`7eb11a705a3f810f669de79ebb351a1c60bed8cbef2397dfc2cd60ce2330f9c7`**. Original bounded GUI timeline and child cleanup PASS; **outer `xvfb-run` process exited 0**.

This is a client/render/menu/isolated protocol smoke test, **not** original authenticated server cooking, inventory changes, sustained online gameplay, or native Windows/GPU acceptance.

## GitHub source-safe deliverables

- `tools/recovery/r308/rebuild_r308_from_pinned.py` — exact SHA-pinned executed builder, Git blob `63dd69ed76a02bb6738272746f75fbd4ce873c50`.
- `tests/java/r308/R308ScenePlacementBoundaryRegression.java` — exact real-class red/green 256-assertion Java test, Git blob `b354a58272b3a32c18da93330260b63a68e69384`.
- `tests/python/r308/R308SourceSafetyRegression.py` — source-only **18/18 PASS** tests of source/binary pins, unique anchors, exact coordinate mappings, invalid inputs, no-write safety and private-file exclusion; Git blob `d11a5d108ffcd50a1d8c2db4eaba0053c780e283`.
- `.github/workflows/v309-r289-windows-safety.yml` now executes R308's source-only tests on hosted Windows Server 2022 and Ubuntu 24.04. Both passed. Hosted CI does not contain private game JARs/cache and must not be described as native game execution.

## Owner-private release (not public GitHub)

`SpawnPK_v309_R308_SCENE_PLACEMENT_BOUNDARY_PRIVATE.zip` — **2,819,505 bytes**, SHA256 **`5fcc45b74db8f276ce143ad82d46f79fa19ddf4f03300eec3963e90134b3f868`**. Two independently created deterministic ZIPs byte-identical, **20 members** and **73** independent SHA256/CRC/manifest/JAR-class-count/compiled-regression/GUI/socket checks PASS. Contents: class-only R308 JAR, authored source-safe builder and regressions, real R307 RED/R308 GREEN, four build logs and Java suites, original GUI screenshots/timeline, actual localhost decoded protocol receipt, private manifest. No original complete client, recovered full source tree, original cache, fonts or credentials included. Do not publish its private class JAR or screenshots to public GitHub.

## Remaining gates

**Native owner Windows R308 GUI and actual GPU radius-50 rendering remain NOT TESTED**, as do original authenticated production server cooking/items and sustained online play. The last owner-native R297 launcher is pinned to older R295 and does not establish R308 acceptance. Keep PR #1142 DRAFT and `main`/installed owner files unchanged; prioritize real owner-native acceptance over more redundant preflight tools.
