# SpawnPK v309 R307 — cold visibility-grid initialization and GPU viewport admission

**20 October 2026.** Two original recovered client classes changed: `rs/Client.class` and `rs/Scene.class`. Real original R306 failures reproduced; actual R307 classes compiled and regression/GUI-tested. Sole-active PR #1142 remains **DRAFT**. No original complete game source, original client executable, original cache, fonts or credentials committed or installed.

## Root causes reproduced on the original compiled R306

**Cold `Scene.drawScene`:** R306 initialized `tileVisibility` to a zero-filled **51×51** array at class load. Its radius-transition guard compared only the array dimensions to `2*activeDrawDistance+1`. On the first frame at the default radius 25 the size already matched, so visibility was **never calculated**, even when valid scene terrain existed. The original real-class regression recorded `R307_COLD_VIEWPORT before=0 after=0 width=0` and failed with `R307_COLD_VIEWPORT_GRID_NEVER_INITIALIZED`.

**GPU `Client.alignViewport`:** The R306 client conditionally called `Scene.setViewport` only when `GpuRenderer.isActive()` was false. The real compiled client with GPU-active flag followed `alignViewport` but left every scene visibility cell false: `R307_GPU_ALIGN_VIEWPORT before=0 after=0`, then `R307_GPU_ALIGN_SKIPPED_SCENE_VISIBILITY`. CPU and GPU scene renderers depend on the same visibility calculation; a mode flag alone must not skip it.

## Minimal original-source production changes

1. In original **`Client.alignViewport`**, remove the `if (!GpuRenderer.isActive())` gate around the existing `Scene.setViewport(500,800,viewportWidth,viewportHeight)`. Alignment initializes scene visibility in both software and GPU modes.
2. In original **`Scene`**, set the static `tileVisibility` field to uninitialized `null` instead of a misleading empty but correctly-sized 51×51 array. The inherited R306 `drawScene` recalculation guard now executes on the first frame.
3. The existing cold-draw `setViewport` call selects its retained viewport dimensions when positive, otherwise falls back to the real `Client.viewportWidth/viewportHeight`. This allows an actual first scene draw before the previous viewport extrema were populated.

Other production classes, original cache, scene model definitions, packets, server endpoints and item logic remain untouched. All prior R290–R306 scene/client guards remain.

**Exact SHA256 source pins:**

| Source | Preimage | R307 postimage |
| --- | --- | --- |
| `rs/Client.java` | `db1dfd4a4752fced78c2cb886bc50159eb8eeb8cc94d27c70b3d9e2ff1b1764c` | `f7d8e18a5e5d0b43e25b579388d06f035e0890dc8d595c41aac56bb316fc9dcf` |
| `rs/Scene.java` | `b8fa016278c1ef8def2866dbffd54bf3a78f7b3bb28985672e1609e7f6787a3d` | `2ed273e3dd162a5b1884f776dfcec2460f49b732ea0206b6211aeca72b3ef092` |

## Genuine complete Java build and regression results

- Three fully independent builds from **exact SHA-pinned private R278/R265 owner original archives**: two using the local full-source compiler, one using the exact **public GitHub reproducible R307 recipe**. Each compiled **1,277 original Java source files** to **1,386 Java 11-target classes**, byte-identical JAR SHA256 **`00204d4b1fe557e64054520e7f22b54bf7094b617784639d50b95c8b8af77d94`**.
- Per-class binary diff against R306: precisely **`rs/Client.class`, `rs/Scene.class` changed**, other **1,384 classes identical**, with no new/removed classes.
- Real R306 JVM tests **RED** on both new regressions. R307 GPU `alignViewport` test **GREEN**: populated visibility cells **0 → 240,282**. R307 direct cold `Scene.drawScene` test **GREEN**: populated cells **0 → 264,676**, retaining fallback width **960**.
- All **106,511 preceding real-client Java assertions/reference comparisons** from R293–R306 rerun against the exact R307 JAR and **PASS**. Includes R305's **102,510-cell** yaw/edge oracle with zero mismatch and R306's 64 transition checks. Both R307 red/green JVM regression programs PASS, making **106,513** total existing checks plus new independent test cases.
- Public-only source safety: **20/20** tests PASS in the local full repository layout and in the hosted Windows Server 2022/Ubuntu 24.04 CI. Hosted CI is source safety only; game binary/cache are private.

## Authentic Linux graphical compatibility

The real compiled R307 class-only JAR was loaded in a disposable test home copied from a previously SHA-verified owner cache. The original source-owned **1400×900 Linux/Xvfb GUI** and Java AWT Robot used a localhost-only synthetic server (**127.0.0.1**). **Full outer Xvfb process exited 0**, and the original client rendered region **13386 / field1134** (98.47% nonblack world crop). Robot selected **Cook** on range object **114**. The isolated server received actual ISAAC-decoded outgoing **opcode132, length 6**, tile **(3362,4769)**, with matched synthetic incoming **opcode253** reply. Exact **51-byte wire SHA256 `09014b8459bf5e98706a92ba2f64ec6c5b6a4ad8ce00d286217a28f5a1674798`**. Client/server/Robot children cleaned up.

This is a genuine Linux default-view graphical compatibility smoke test, **not actual native Windows GPU rendering** or original online-server cooking/item creation.

## Public GitHub source-safe provenance

- `tools/recovery/r307/rebuild_r307_from_pinned.py`, Git blob **`3f35b30a36ecc0c996c61f09a97bf1393ccee0a0`**, byte-for-byte identical to the executed third full compile. Checks original R278/R265 ZIP SHA, R278 original rebuilder and old compiled JAR, SHA256-pinned public R302–R306 patch functions, both old/new `Client` and `Scene` source hashes, 1,277-source count, 1,386-class count and exact new JAR SHA, and refuses overwriting owner outputs. Does **not** embed any private original Java.
- `tests/java/r307/R307GPUViewportRegression.java` and `R307ColdViewportRegression.java`: exactly the two compiled real R306 RED / R307 GREEN tests.
- `tests/python/r307/R307SourceSafetyRegression.py`, Git blob **`afe3766c24d7df574500b405231c766aa45b96ab`**, 20/20 source-only provenance and refusal checks added to Windows/Linux CI.
- Existing `.github/workflows/v309-r289-windows-safety.yml` now runs R307 tests without exposing private game binaries.

## Owner-private deterministic release

**`SpawnPK_v309_R307_COLD_GPU_VIEWPORT_INITIALIZATION_PRIVATE.zip`** — **3,191,622 bytes**, SHA256 **`b37c5f06e6b0ede7687818abfefb9c02c166276f28ceb6d3ac17bff8d4ae10ed`**. Two independent deterministic ZIP builds byte-for-byte identical; independent **97/97** integrity/provenance/actual-gameplay-evidence checks PASS. **26 ZIP entries**: privately compiled 1,386-class R307 JAR; public-safe builder and tests; original R306 RED/R307 GREEN and previous regressions; three full compile logs; GUI screenshots, decoded socket data/ack, and manifest. **No original complete client, original cache, full recovered Java source tree, original fonts, or credentials.** Never publish this private class JAR or its original-game screenshots to a public GitHub repository.

## Still unverified

**Native Windows R307 GPU/GUI: NOT TESTED.** The two Java tests simulate the GPU-active path and real viewport calculations, but do not validate a native graphics driver or 50-tile GPU rendering. Original online-server cooking, inventory/economy and sustained authenticated runtime: NOT TESTED. The previous R297 Win32 acceptance launcher still pins R295, not R307. Keep PR #1142 **DRAFT**, do not merge `main`, and do not install/overwrite owner files without native acceptance.
