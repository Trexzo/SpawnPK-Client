# SpawnPK v309 R305 — viewport outer-edge completion and 32-yaw seam

**2026-10-20.** Real recovered Java renderer defect fixed in one class. PR #1142 remains **DRAFT**. No owner-machine installation, `main` merge or original game/cache/source files committed publicly.

## Genuine R304 failure

The previous R304 correction made viewport visibility allocations and occluder indices radius-dependent, but `Scene.setViewport` still had two independent correctness defects:

1. Smoothing loops traversed `-activeDrawDistance <= x < activeDrawDistance` and likewise Y, even though the output grid contains `2 * activeDrawDistance + 1` cells. The entire positive outer row/column was never populated.
2. Two adjacent-yaw samples used `(yaw + 1) % 31` even though there are **32 yaw bands**. Yaw band 30 incorrectly blended against yaw 0 rather than 31; band 31 incorrectly blended against 1 rather than 0.

A separate independently computed projection/visibility reference oracle invoked the **actual compiled R304 client** across draw distances 5, 10, 25, 30 and **50**. Across **102,510** sampled viewport cells, it recorded **3,535 mismatches** (743 at the positive outer edge and 2,792 at interior yaw transitions).

## R305 production source change

Only `rs/Scene.java`, inside `setViewport`, changed four original tokens:
- `var21 < activeDrawDistance` -> `var21 <= activeDrawDistance`;
- `var22 < activeDrawDistance` -> `var22 <= activeDrawDistance`;
- both `(var20 + 1) % 31` -> `(var20 + 1) % 32`.

No object models, collision, transport, cache, network behavior or NPC/gameplay action changed; previous R290–R304 production source fixes remain. Original R304 Scene source SHA256 **`839492e3d66ea546699f18338f09135e9787ff0c40ef193517cb18e68f8accd4`**, R305 postimage SHA256 **`dd02b8627053d7a9dc1c6f932cb34c5e78c4c5d21103a06ca169199f8b49f17e`**.

## Real compiled Java testing

- The **same independent oracle**, run against the genuine R305 compiled client, now passes all **102,510/102,510** viewport comparisons with **0 mismatches**, including extended radius 50, yaw 30→31 and 31→0, positive scene-grid edges.
- All original R293–R304 authentic client JVM regressions rerun on the R305 JAR: **3,937/3,937 PASS**.
- Combined **106,447/106,447 actual JVM assertions/reference comparisons PASS**.
- Three complete builds from the original SHA-pinned owner R278 and R265 archives, **1,277 original Java sources → 1,386 Java 11-target classes**, produced byte-identical R305 class-only JAR SHA256 **`df44dd354dd7df5c6cbbaa5d3093bfe1db6353009c921e7201068b94e15ceae1`**.
- Original R304 → R305 binary class comparison: exactly **one** changed class, `rs/Scene.class`; other **1,385** compiled classes byte-identical.
- One of the complete builds was done by the **exact public SHA-pinned R305 builder**, preserving the prior R304/R303/R302 source, dependency, compiler, class-count and output hash checks. It refuses unrecognized source input and occupied output destinations.

## Actual Linux GUI compatibility

A disposable GUI test home, copied from a previously verified authentic owner cache (10,772 files), ran the exact R305 class-only JAR using the original source-owned bounded localhost synthetic game server and Java AWT Robot. **Full outer Linux/Xvfb process exit 0**; original rendered OSRS region **13386 / field1134**, 1400×900 screen, viewport nonblack fraction **98.454%**. Robot selected **Cook** on range ID **114**, and the isolated server decoded outbound **opcode132, length6, tile(3362,4769)** and returned paired synthetic **opcode253** reply. Genuine **51-byte** socket SHA256 **`3ccca6d144b8c6f646b2dcfaa4c3b05059fac79d3d8feec4e195abf3028a1f14`**. All children cleaned.

**The graphical replay is a compatibility smoke test at its default view**, not a visual GPU radius-50 screenshot comparison or native owner-Windows acceptance; the expanded radius-50 correctness is independently verified in the genuine JVM visibility calculations, not on a native GPU display.

## Source-only public GitHub changes

- `tools/recovery/r305/rebuild_r305_from_pinned.py`, exact build-tested Git blob **`d1a51d6e34bc445e694409d84adac7cf782ba5db`**; pins original R304 source-safe builder SHA, existing R304 Scene preimage, R305 postimage, and rebuilt class-JAR SHA.
- `tests/java/r305/R305VisibilityGridOracle.java`, exact original red/green independent reference regression, Git blob **`2758d452885dbac33b92a78dd2bb204463be58b9`**.
- `tests/python/r305/R305SourceSafetyRegression.py`, Git blob **`716706e2475b5c12c64df66a713eb71dbddf4fbb`**; **16/16** tests for SHA pins, source drift, grid geometry, no-overwrite and exclusion of proprietary binary files. Runs in the hosted Windows2022/Ubuntu24.04 source-safety matrix.
- Hosted CI contains no original private game JAR/cache, so the hosted green result demonstrates **source-only** checks, not genuine gameplay/Java client execution.

## Owner-private release

`SpawnPK_v309_R305_VISIBILITY_GRID_YAW_SEAM_PRIVATE.zip` — **3,190,860 bytes**, SHA256 **`58ad9288c1c1c120ea0efab3fcb8adf811beb7651ca86b5a0757c6c754af4a6e`**, 25 ZIP members. Two independently created deterministic ZIPs are byte-identical; independent manifest/member SHA256 and CRC, exact class-JAR hash, original R304 red versus R305 green, old Java regressions, GUI screenshots and genuine wire/ack validation all pass. Contains the class-only R305 JAR, public-safe builder/tests and owner-private test evidence; **no** complete original client, cache, complete recovered original Java source, fonts, credentials or owner configuration. Do not publish its original game screenshots or proprietary compiled classes on public GitHub.

## Remaining acceptance boundary

Native owner Windows R305 GUI: **NOT TESTED**. Native GPU-specific extended rendering at radius 50: **NOT TESTED** (visibility JVM calculation is tested). Original authenticated live server cooking/inventory and sustained production gameplay: **NOT TESTED**. The older R297 Windows launcher targets R295 and does not verify R305. Keep PR #1142 draft; do not merge, alter the installed owner client, or infer native Windows behavior from source-only CI.
