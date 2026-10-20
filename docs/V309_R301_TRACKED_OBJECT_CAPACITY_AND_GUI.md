# SpawnPK v309 R301 — tracked scene-object capacity is checked before insertion

**20 October 2026 — recovered Java client production fix, real-class tests and Linux GUI witness.** All private original assets, cache and recovered game source remain out of public GitHub. Keep sole active PR #1142 **DRAFT**, with no change to installed owner clients or `main`.

## Actual R300 defect reproduced

The two `Scene` object-footprint insertion paths `method3408` and `method2959` manage a **fixed 5,000-entry tracked-object table**. In the genuine compiled R300 client, invoking a tracked insertion with an invalid `field5665` counter causes `ArrayIndexOutOfBoundsException`. Some paths can already alter a scene tile before writing the object tracking slot, so failure can leave a partially modified scene. The source-level insertion footprint guards added in R300 did not check tracking capacity.

The exact authentic R300 red test records `R301_SCENE_OBJECT_CAPACITY_CRASH method=method3408 tracked=true ... Index -1 out of bounds for length 5000`. This is separate from off-map footprint validation.

## Minimal production change

One new `hasTrackedObjectCapacity()` helper checks that `field5665` is nonnegative and below the lengths of **both tracking arrays**. Both insertion methods use it, conditioned on the existing `var11` tracked-object flag, **before modifying any tile**. Invalid tracked capacity returns false, leaving the tile and counter unchanged. Untracked insertion does not require an available tracked slot.

The R300 recovered `source/rs/Scene.java` SHA256 preimage is **`85367ddd248e15192ef2bffa55ed764b48b67fedfb3378f9bf7d419337affca8`**; R301 postimage SHA256 **`27ba14ea218df3f4c377f76809ccb749c45ef6dee02d628f262ab99f7e3d1e49`**. All R290–R300 menu/scene safety checks remain; no original object definition, opcode, network endpoint, rendering, asset or server behavior changed.

## Compiled evidence and exact reproducible recovery

All **1,277** genuine Java files compiled to **1,386** Java 11-target classes, using the exact pinned original private R278 and R265 inputs. Two independent full builds produced the identical class-only JAR SHA256:

```text
e741150b360e01f0adf098c977843507a7ff4cc9c872451cf6461415ed2f58da
```

A per-class comparison against the actual R300 compiled JAR found **only `rs/Scene.class` changed**; all other **1,385 classes byte-identical**.

The exact tested, owner-source SHA-pinned builder `tools/recovery/r301/rebuild_r301_from_pinned.py` has Git blob **`5da7412e11a6b61ff4c2b45b1c71b03827916402`**, byte-for-byte identical to the original real two-build script. It fails closed on unrecognized private inputs, source preimage/postimage, incorrect compiled class count/JAR SHA, and already occupied output paths.

**Real JVM tests independently rerun after R301:**

| Authentic real-client suite | Pass |
| --- | ---: |
| R301 tracked capacity, atomic rejection and valid insertions | 42/42 |
| R300 planes, bridge and object footprints | 82/82 |
| R299 small scene mutators | 136/136 |
| R298 read-only scene queries | 192/192 |
| R295 `getHashAtTile` boundaries | 69/69 |
| R293 object menu boundaries | 71/71 |
| **Total** | **592/592** |

The R293 test was run under Xvfb to provide an AWT display for the genuine client Applet; in a headless JVM it throws `HeadlessException` before reaching its regression cases. This was handled by using Xvfb, **not by weakening the test**. The original R301 Java regression Git blob **`dcab94cea6f3733fbf67408992b59774f0112ffb`** is byte-identical to the actual R300 RED and R301 GREEN executed source.

## Actual R301 Linux graphical behavior

A bounded Linux/Xvfb session loaded the **R301 source-built class JAR** with previously SHA-verified original cache resources and the original source-owned local mock server. The original reconstructed client rendered region **13386 / field1134** at 1400×900. Java Robot selected **Cook** on Cooking range object ID **114**; the independent localhost test server decoded outbound **opcode132**, six-byte request world(3362,4769), and returned synthetic **opcode253** acknowledgment for object114. The replay logged `R285_BOUND_ISOLATED_OSRS_COOK_GUI_PASS` and `R285_SESSION_TERMINATED status=PASS` with bounded Java-client and local-server cleanup.

The authentic socket trace was **51 bytes**, SHA256 **`b44e78fec43c0ccd7bf1b7b7360ac3c478920577649b13b168e1b25fe0ea465b`**. The private evidence contains original rendered screenshots, client/server/Robot logs, received bytes, JSON receipt and timeline.

This is a **single** genuine Linux client GUI replay against an isolated synthetic localhost server, not native Windows or original authenticated online cooking/item production.

## Public GitHub and owner-private release

Public safe artifacts:

- `tools/recovery/r301/rebuild_r301_from_pinned.py` — exact original source-pinned builder, Git blob `5da7412e11a6b61ff4c2b45b1c71b03827916402`.
- `tests/java/r301/R301PlacementCapacityRegression.java` — actual 42-case real-client red/green test, Git blob `dcab94cea6f3733fbf67408992b59774f0112ffb`.
- `tests/python/r301/R301SourceSafetyRegression.py` — **18/18** public-only source, capacity and fail-closed checks, Git blob `36ce0964a4df8975971e5468a38d323ba43fbd89`; included in hosted Windows2022/Ubuntu24 source-safety CI.

Owner-private release, **not pushed as a public GitHub binary**:

`SpawnPK_v309_R301_TRACKED_OBJECT_CAPACITY_PRIVATE.zip`, **2,972,201 bytes**, SHA256 **`4888cb2783aebe23f9b86b2a6a34352a3e7a00777fa642cc80700000ec8da5c7`**. Two deterministic byte-identical builds, **77 independent ZIP/manifest/CRC/source/pass and GUI-socket checks**. Includes the R301 class-only JAR, authored build/test scripts, red/green and full Java suite logs, three Linux screenshots, local wire/receipt, manifest. It excludes original full client executable, original cache, complete recovered original source tree, fonts or credentials.

## Remaining acceptance boundary

**Native owner-Windows R301 graphical acceptance: NOT TESTED.** The last owner-specific Windows launcher R297 pins an older **R295** JAR, so its green source-level tests cannot prove R301 Windows behavior. Original authenticated live server, actual cooking items/inventory and sustained online runtime were not tested. PR #1142 remains draft; no merge or installation.

Next worthwhile work: owner-native R301 graphical evidence or concrete additional gameplay defects, not another unneeded source-only readiness layer.
