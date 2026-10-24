# SpawnPK v309 R300 — scene plane, bridge and object-placement bounds

**2026-10-20. Real owner-private client source change; PR #1142 remains DRAFT.** No original cache, full private game source tree, complete original client JAR, fonts, credentials or private compiled game classes are committed to public GitHub. No user-installed client was modified or merged to `main`.

## Reproduced original R299 defect

The original SHA-pinned, source-built R299 JAR (`9c4d4350918c05c4a9f40d9372cab8c77088c76a43a32eb7f46b6974d57738cc`) crashes on `Scene.setPlane(-1)`:

```
R300_SCENE_BOUNDARY_CRASH setPlane(-1)
java.lang.ArrayIndexOutOfBoundsException: Index -1 out of bounds for length 4
at rs.Scene.setPlane
```

This happens before the earlier R299 small-mutation bounds checks run. The underlying scene plane, bridge-shift and two object-footprint entry points also accessed unchecked array indices or could accept malformed footprints. The real-class regression covers both invalid and valid paths; it is not a source-only fixture.

## Minimal production patch

The original R299 `source/rs/Scene.java` SHA256 preimage was **`007159b0b47058552150985c45f5b441df1a4bbd5a794bc41b6ad172bee8832e`**. R300 postimage SHA256 is **`85367ddd248e15192ef2bffa55ed764b48b67fedfb3378f9bf7d419337affca8`**.

Four entry points are protected without modifying valid behavior:

1. `setPlane(int plane)` refuses a plane outside `[0, tiles.length)` *before assigning the plane field* or populating the tile grid.
2. `method3365(int y,int x)` refuses a tile outside the 104×104 scene before bridge-plane shifts, preserving previous valid tile references and clearing plane 3 normally.
3. `method3408(...)` and `method2959(...)` (the two private object-footprint builders) share a new `isSceneFootprintInBounds` guard. It rejects invalid planes, nonpositive dimensions, and footprints outside the scene. It uses subtraction for width/height boundary checks, avoiding addition overflow.
4. All preceding R290/R293 menu object-authority, R295 scene hash, R298 read-only getter, and R299 seven small-mutation guards remain intact.

No opcode/packet protocol, object definitions, cache files, network destination, scene rendering, collision or original server behavior changed.

## Genuine private source build and regression proof

- Two independent **full original Java 11 target builds**, each **1,277 source files → 1,386 classes**, produced byte-identical class-only JAR SHA256 **`a3ece2b2be3559777c140c93fc5d4a33499ccf45d9c5172e1bc53e4f439a2371`**.
- Per-class binary comparison against the actual R299 compiled JAR: **only `rs/Scene.class` changed**; all other **1,385 classes byte-identical**.
- Exact original R299 compiled client **fails** the new `R300SceneEntrypointRegression` on `setPlane(-1)`; the same new regression on R300 **82/82 PASS**. It covers negative/excessive/extreme planes and bridge coordinates, invalid object planes/footprint dimensions/coordinates, normal plane population, intact bridge shifting/lower-tile references, and positive object insertion and occupancy.
- Previously established genuine R293 object menu **71/71**, R295 hash **69/69**, R298 read-only **192/192**, and R299 mutation **136/136** suites recompiled against the R300 JAR and all passed. **Total: 550/550 real-client JVM assertions.** The R293 test requires the original owner's exact private R239/R218 dependencies to initialize the genuine `Client`; those dependencies were used in the private JVM execution and are not committed.
- The exact SHA-locked `tools/recovery/r300/rebuild_r300_from_pinned.py` was used to reproduce the JAR after hash discovery; it fails closed on unexpected R278/R265 private ZIPs, old source hashes, ambiguous insertion anchors, incorrect resulting source hashes, unexpected JAR hash or existing output. Git blob **`8c9f7ee0ca2af8580f6bcbeb99ff4fe2d2d8c1b5`** is byte-identical to the executed pinned builder.

## Authentic client graphical test — Linux only

Two separate Linux/Xvfb GUI sessions ran the exact **R300 class-only JAR** on a disposable copy of the previously SHA-verified 10,772-file private R299 test home. They used the original R285 local synthetic server, actual reconstructed 3D OSRS region **13386 / field1134**, Java AWT Robot Cook interaction against range ID **114**, actual ISAAC-decoded outbound opcode **132** (six-byte object action at world **3362,4769**), and matched synthetic localhost incoming opcode **253**. Both **inner GUI timelines recorded PASS** and completed bounded Java client/server cleanup.

The second replay's **outer `xvfb-run` process returned exit code 0**. Its 52-byte received socket ciphertext SHA256 was **`e8ef8f320cbabfcf821eb1995b87224578dcedbaed63090044edfa5ef1d829f3`**. The first replay's distinct 52-byte socket SHA256 was **`33e1bd026ed7bf9e6acbe843d4ae51717dd7bcea7802b69ef93aafb6d18172bb`**, with an inner GUI PASS; that initial background launch did not retain an independently recorded outer exit code and must not be presented as two outer exit-code proofs.

These sessions reused an isolated authentic cache home; they were **not** two separate complete private archive intakes. No native owner Windows R300 GUI run or original authenticated game-server cooking/inventory effects are established.

## Source-safe GitHub and owner-private release

- `tools/recovery/r300/rebuild_r300_from_pinned.py` — exact executed source-pinned builder, Git blob `8c9f7ee0ca2af8580f6bcbeb99ff4fe2d2d8c1b5`.
- `tests/java/r300/R300SceneEntrypointRegression.java` — source-safe real `Scene` regression covering plane, bridge and both object insertion helpers.
- `tests/python/r300/R300SourceSafetyRegression.py` — **18** source-only trust, boundary, fail-closed and no-private-binary tests; Git blob `81ffa9456e699fd277b42e13d186372bd77e01e2`; this was executed locally and added to the Windows 2022 / Ubuntu 24.04 GitHub source-safety matrix.
- The GitHub CI has **no original private game archives** and its green result covers source-safety contracts, not authentic JVM or GUI execution.

**Owner-private ZIP:** `SpawnPK_v309_R300_SCENE_ENTRYPOINT_AUTHORITY_PRIVATE.zip`, **3,565,130 bytes**, SHA256 **`b6cd46d0865288ee2039eeef0d93bdde77252a8a8e9979f4da1fe928d38233fd`**, 33 entries. It contains the rebuilt R300 class-only JAR, reproducible public-safe builder and Java/Python tests, actual original R299 red and R300 green results, two full build logs, both Linux client/server/robot/screenshot/socket receipts and manifest. Two independent deterministic builds were byte-identical, with archive and manifest SHA validation. No original game cache, complete recovered Java source, original full client JAR, fonts, credentials, or installed owner files are included. The private binary/evidence ZIP **is not committed publicly**.

## Remaining acceptance boundary

**Owner-native Windows R300 GUI: NOT TESTED.** The existing Windows acceptance tool R297 targets the older R295 JAR and cannot establish R300 acceptance. No original online server, authenticated login, production cooking/inventory/economy effect or sustained game runtime is verified by the local synthetic protocol test. Keep PR #1142 DRAFT and owner-installed client unchanged. Future effort should favor real native owner acceptance or concrete new gameplay bugs rather than adding further redundant preflight wrappers.
