# SpawnPK v309 R302 — static Scene occluder capacity

**20 October 2026.** Real original-source client correction, privately built and tested. PR #1142 remains DRAFT; no owner-machine installation, no merge, and no proprietary recovered source/cache/client binary on public GitHub.

## Reproduced defect

The genuine source-built R301 class-only JAR throws `ArrayIndexOutOfBoundsException` in `Scene.method345(-1,...)`: the static scene occluder writer directly indexes `field5682[plane][field5681[plane]++]` without validating the plane or the table's 500-entry capacity. The counter may also advance before an out-of-range slot assignment fails. The original R301 JAR's failure is preserved in `RED_R301.log`.

The R302 patch changes only the start of **`public static void Scene.method345(...)`**, checking both static table references, plane bounds, row availability, nonnegative counter and remaining row capacity before allocating/storing an Occluder. Invalid inputs become no-ops. The **four plane tables and 500 slots per plane** remain unchanged; all valid rendering occluders can still be inserted. This also prevents late inserts after the static tables have been released. No original scene geometry, texture, client/network opcode, object definition, cache, remote endpoint or other production class changes.

**Original R301 Scene.java SHA256** `27ba14ea218df3f4c377f76809ccb749c45ef6dee02d628f262ab99f7e3d1e49`; **R302 source postimage SHA256** `ec91cf02318dc26a80a4a5e5ee9e912feff8a66ee83e37e2d82b25ada321bc66`.

## Genuine Java and graphical evidence

- SHA-pinned original private R278/R265 inputs: **1,277 Java sources**, `javac --release 11`, **1,386 classes**; **two independent byte-identical** complete builds. R302 class-only JAR SHA256 **`f3ce35078a1ebf07314de6c7335a9a9d66b990c587730fdf07a452f23bec5fae`**.
- Per-class binary comparison with the genuine R301 JAR: **only `rs/Scene.class` changed**, **1,385** classes byte-identical.
- Actual R301 JAR **RED**: invalid plane `-1` throws `ArrayIndexOutOfBoundsException` in `Scene.method345`.
- Actual R302 JAR **GREEN, 1,016/1,016 checks**: invalid/extreme planes, corrupt/negative/full counters, all 500 valid sequential slot insertions, independent plane counts and final-slot insertion, null post-shutdown tables and preservation of rejected counters.
- Previously established actual-client regressions were rerun on R302: R293 menu **71**, R295 scene-hash **69**, R298 read-only queries **192**, R299 mutation bounds **136**, R300 scene entry points **82**, R301 tracked-object capacity **42**: **592/592 PASS**. **Total 1,608/1,608 real-client Java assertions**. The AWT-requiring R293 suite ran under Xvfb.
- Authentic-cache Linux/Xvfb graphical session against the rebuilt R302 client: **outer process exit 0**, actual region **13386 / field1134**, 1400×900 rendered viewport, Robot **Cook** on range ID **114**, real ISAAC-decoded outgoing **opcode 132 / six-byte** object action at world **(3362,4769)** and matched synthetic localhost incoming **opcode 253**, independent server receipt, bounded child cleanup. Captured **52-byte** wire SHA256 **`cef26c1f5ad06b70a2d8e25b7e83f81076910dfdd00975d35e4685a3bbb77314`**. Uses an isolated copy of an already SHA-verified original-cache home, not a new archive intake.

## Public GitHub

- `tools/recovery/r302/rebuild_r302_from_pinned.py` — SHA-locked original owner inputs, exact R301 scene preimage/R302 postimage, original source patch sequence, strict resulting private JAR SHA and no-overwrite destination. Git blob **`1c7a558973a61da6f5126a9a2c7c7a2e9a02ef25`**, byte-identical to the actual full-source rebuild script.
- `tests/java/r302/R302OccluderCapacityRegression.java` — exact original red/green real compiled-client regression. Git blob **`7236e584b1f2280800b1d6cb248e85c32e6bcfbc`**.
- `tests/python/r302/R302SourceSafetyRegression.py` — **18/18 PASS** source-only hash, unique anchor, invalid input, missing/damaged provenance, no-asset tests. Git blob **`1da3d146577eb0dbe02486f06a270fdfd638e826`**. Run in hosted Windows Server 2022 and Ubuntu 24.04 CI.
- Hosted CI contains **no private game files**, so its green result covers only source-safety tests, not real class compilation or graphics. Real private evidence was checked locally.

## Owner-private release (not published to GitHub)

`SpawnPK_v309_R302_SCENE_OCCLUDER_CAPACITY_PRIVATE.zip` — **3,194,202 bytes**, SHA256 **`6281dc570b4f3b4713dff22c1cfd0d150e01bffb8c1848bff581f70bc511cb37`**, **25 ZIP members**. Two independently created byte-identical deterministic ZIPs; independent verifier **103/103 checks PASS** over member CRC, SHA, exact 1,386-class JAR, original source/build evidence, GUI screenshots and socket receipt. Contains only the reconstructed class-only JAR, authored reproducibility/test scripts and private test evidence; excludes the original complete client executable, full recovered source tree, original cache, owner configuration, fonts and credentials.

## Acceptance boundaries

**Native owner Windows R302 GUI NOT TESTED.** The latest previous native Windows acceptance script R297 pins R295, not R302. Original authenticated live server, actual cooking item production/inventory, sustained gameplay and Windows owner rendering NOT demonstrated. No changes were installed or merged. The PR remains DRAFT. Next work should seek native R302 owner Windows acceptance or another concrete original-client defect rather than repeating preflight layers.
