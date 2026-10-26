# SpawnPK v309 R295 — real scene-hash lookup bounds + isolated GUI evidence

**2026-10-19.** Production change is limited to **`rs/Scene.class`** and its original Java source. All recovered private binaries/cache remain owner-private. Same draft PR #1142 and coordination issue #1117; no merge, no installation.

## Reproduced defect: lower-level Scene access still throws after R293

The R293 client correctly rejects off-scene object-menu actions in `Client.handleObjectClick`. However **direct calls to `Scene.getHashAtTile(plane,x,y,objectHash)`** still indexed `this.tiles[plane][x][y]` without validating coordinates. A real Java regression on the exact compiled R293 private class JAR raised:

`R295_SCENE_HASH_DIRECT_OOB_CRASH plane=0 x=-1 y=0` caused by `java.lang.ArrayIndexOutOfBoundsException: Index -1 out of bounds for length 104` in `rs.Scene.getHashAtTile`.

This is a separate lower-level defensive correctness defect; do not conflate it with R293's menu-specific correction.

## Actual minimal source fix

Inside `source/rs/Scene.java`, `public int getHashAtTile(int var1,int var2,int var3,int var4)`, **before** the scene array read:

```java
if (var1 < 0 || var1 >= this.tiles.length
        || var2 < 0 || var2 >= this.tiles[var1].length
        || var3 < 0 || var3 >= this.tiles[var1][var2].length) {
    return -1;
}
```

The existing absence sentinel `-1` is preserved. No object IDs, cache definitions, opcodes, menu actions, network endpoints, or GUI logic changed. The **previous R293 `Client.class` and other 1,384 non-Scene classes remain byte-identical**.

### Actual private build and Java regressions

- Reconstructed from the **exact pinned original R278/R265 private input archives**, without committing recovered source.
- Source `Scene.java` SHA256 **before** `5757842cf0cea18bcd99667ddeba5150ec915e450308ca07ff45ee3922fdf6b1`; **after** `24790fc3aac8676df95c1cd0f830f26bc6ad749cc87435f47b9eb69c9c8ef813`. R293 client postimage SHA pins still checked.
- **1,277 real Java source files** compiled with `javac --release 11` into **1,386 classes**, twice. Both compiled R295 class-only JARs byte-identical SHA256 **`f5b6f4b6ea3e5e8fc49e1cbe61197647ed7c1e238a49d935c77882cb40da2e35`**.
- Actual original R293 JAR fails `R295SceneHashBoundsRegression` on invalid scene X=-1. Rebuilt R295 JAR passes **69/69** direct scene lookups (invalid plane/X/Y/extreme inputs, legitimate empty in-range scene and border tiles).
- Original R293 object-menu stale-scene action regression still passes **71/71** on R295.
- Binary comparison confirms exactly **one changed compiled class: `rs/Scene.class`**; other **1,385 classes byte-for-byte unchanged**.

## Real GUI evidence — distinguish the two scopes

Two independent owner-private R295 Linux/Xvfb sessions from exact original archives staged all **10,772 authentic cache files** each. The **inner graphical test harness** in both runs logged `R285_BOUND_ISOLATED_OSRS_COOK_GUI_PASS` and `R285_SESSION_TERMINATED status=PASS`, displayed OSRS region **13386 / field1134**, and sent real ISAAC-decoded **Cook object 114 / opcode132 / six-byte world (3362,4769)** interactions through an isolated localhost test server, followed by paired synthetic **opcode253** replies.

Real separate 52-byte socket traces SHA256:

- Fresh inner session 1: `bf32b2fed1c6d3edcd65c7e3fdf9ee8066c2304c26630ecbc7883394ca0aecfd`
- Fresh inner session 2: `44b44c5209fd2f3e02b4a75ddac3938c0ff29ae8bfe65d49c5b02f221ef86267`

**Important outstanding problem:** Both **outer Xvfb archive wrappers timed out without a final `R295_R295_FRESH_GUI_COOK_PASS` success line**, *after* their nested GUI tests had passed and cleaned up the four child processes. A separate bounded process-group reaping attempt also failed to establish a completed outer wrapper. Therefore **do not claim full end-to-end R295 GUI wrapper acceptance**. The two **inner GUI/real screenshot/actual local socket packet** results are narrower, independently supported facts. Original online-server cooking, Windows, client installer, login, and sustained runtime remain unverified.

The private GUI evidence ZIP has independently passed **160/160 checks**, verifying member CRC/SHA, receipts, opcode132/253, synthetic reply source, real rendered 1400×900 PNGs (nonblack viewport 95%+), distinct session screenshots and socket ciphertext, client/server/robot logs, child cleanup, and **absence** of final outer wrapper success markers. Its verifier refuses to treat those timed-out wrappers as passed.

## GitHub and private deliverables

**Source-safe public commits:**

- `tools/recovery/r295/rebuild_r295_from_pinned.py`: byte-identical to the twice-executed private deterministic full-source rebuild, SHA1 Git blob `19f989eac5e433d4bb36f4ef09aa3883854a64ea`.
- `tests/java/r295/R295SceneHashBoundsRegression.java`: exact **red on R293 / 69 green on R295** authentic-class test, Git blob `74a8af8ffcc7e5c00643558f3d33def198499b54`.
- `tests/python/r295/R295SourceSafetyRegression.py`: **20/20** source-pinning, preimage, postimage, failure-path and binary-exclusion tests, Git blob `22fa9605fe0d3346e4d2ee77263fca44d97dac21`.
- `tests/python/r295/R295CoreGUIEvidenceVerifier.py`: byte-identical to the actual **160-check private GUI evidence verifier**, Git blob `92515229bcdc54851219021b2722be6fb3875748`.
- Existing GitHub CI source-only Windows Server 2022 + Ubuntu 24.04 matrix runs the **20-case** R295 suite; no owner-private input is available to that hosted CI, so its pass is NOT evidence of Java compilation or game GUI.

**Owner-private build ZIP**: `SpawnPK_v309_R295_SCENE_HASH_BOUNDS_PRIVATE.zip`, **2,375,889 bytes**, SHA256 **`277fb5016d60e5b36bb22cede2b3b2500b9773636f433c65774db18a34e401f6`**. Deterministically built twice with byte-identical ZIPs; includes compiled class-only R295 JAR, public-safe build/test sources and red/green Java/build logs; excludes original cache, original full recovered source tree, original complete client, fonts and credentials.

**Owner-private two-session GUI receipts ZIP**: `SpawnPK_v309_R295_TWO_CORE_GUI_RECEIPTS_PRIVATE.zip`, **1,184,123 bytes**, SHA256 **`1d6be7828589db53a3174dec111de78cf319da3c5f34bb0eb7dbb5fc7bb1d5c1`**. Two deterministic identical builds, 160/160 integrity and witness checks. It includes PNG screenshots, actual wire data, logs, timelines, manifest and authored verifier, but no compiled game classes or original cache.

## Next blockers

1. Diagnose **the outer Xvfb wrapper completion/termination hang** with process-level instrumentation; do not turn an inner status line into outer acceptance.
2. Extend the owner-native Windows acceptance test to **R295** (R292 pins R290 and cannot verify R295). Run this only against an interactive owner desktop with all exact hash-locked private files, preserving synthetic localhost-only traffic.
3. Continue with additional authentic client gameplay defects once supported by a failing real-client regression.

PR #1142 stays DRAFT, no `main` merge and no owner-machine modifications.
