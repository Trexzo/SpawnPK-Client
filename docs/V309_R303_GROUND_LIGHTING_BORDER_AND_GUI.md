# SpawnPK v309 R303 — authentic scene-edge ground-object lighting

**2026-10-20.** Real recovered client `rs/Scene` source fix, independently reproduced and tested. Sole active PR #1142 stays **DRAFT**. No original complete game client, recovered full Java tree, original cache, credentials, fonts or private compiled game classes published in GitHub. No owner PC installation or `main` merge.

## Actual defect and scope

The real source-built **R302** client has an off-by-one boundary defect inside **`Scene.method1018`**, the private ground-object model-lighting neighbor lookup. For a legitimate eastern edge tile at local scene `x=103`, `method1018(103,0,null,0)` erroneously satisfies `x < field5663` and accesses `tiles[0][104][0]` instead of refusing the out-of-scene neighbor. The real R302 JAR raises `ArrayIndexOutOfBoundsException: Index 104 out of bounds for length 104`; this was directly reproduced with reflective invocation on the **authentic compiled Scene class**. The southern edge had the equivalent `y+1` defect, and the diagonal checks shared the same off-by-one limits.

## Production source change

Only `Scene.method1018` changed:
- A source-owned `isSceneTileInBounds(plane,x,y)` check rejects invalid starting tiles before neighboring scene lookups.
- East and southeast/southwest neighbor access now require `x < field5663 - 1`.
- South and southeast neighbor access now require `y < field5664 - 1`; this also corrects the original south lookup that compared `y` to the X-dimension `field5663`.
- The existing lighting/model blending calls for valid neighboring tiles are untouched. No scene object definitions, object packets, cache, renderer selection, network endpoints, or other Java classes changed.

Source `Scene.java` SHA256 **R302 preimage**: `ec91cf02318dc26a80a4a5e5ee9e912feff8a66ee83e37e2d82b25ada321bc66`; **R303 postimage**: `ee0660154ab0e289448194a476fc6b2629ea83e1d99ba7477755e6f4885f93b6`.

## Authentic compiled client evidence

- **RED on R302**: real `Scene.method1018` throws `ArrayIndexOutOfBoundsException` at local `(103,0)`.
- **GREEN on R303**: `R303GroundLightingBorderRegression` **1,708/1,708 assertions**, covering all four plane levels and every point on all four scene borders, valid interior tiles and invalid/extreme coordinates. No fake production Java types.
- All earlier authentic Java regressions remain **1,608/1,608 PASS**: R302 occluder 1,016; R301 tracked capacity 42; R300 scene/bridge/placement 82; R299 mutations 136; R298 getters 192; R295 scene hash 69; R293 menu 71. **Total 3,316/3,316** real JVM assertions.
- Exact SHA-pinned original owner **R278/R265** inputs, **1,277 original Java sources → 1,386 Java 11-target classes**. Two independent full-source builds produced byte-identical class-only R303 JAR SHA256 **`a9ae098a79aac6c53eca5a986773b8c79f998b435d181bfde859c283a866b12b`**.
- Binary class diff against exact R302 private JAR: **only `rs/Scene.class` changed**; other **1,385 classes byte-identical**.
- A separate independent build using the **publicly committed R303 wrapper script** also produced the exact same R303 JAR. The R303 wrapper SHA-locks and calls the unchanged public R302 builder, composes just the validated lighting fix, and verifies both resulting source and binary digests. Unlike copying the full prior builder, this keeps the public maintenance path modular.

## Graphical compatibility evidence

One genuine Linux/Xvfb **1400×900** graphical test launched the exact R303 class-only JAR with previously SHA-verified original cached resources in a **disposable isolated test home**. Original Java AWT Robot selected **Cook** on Cooking range object **114** after the client loaded authentic OSRS region **13386 / field1134**, and the localhost-only synthetic server received an ISAAC-decoded outgoing **opcode132, length6**, tile **(3362,4769)**, with matched synthetic incoming **opcode253**. The full bounded GUI runner and **outer Xvfb process exited 0**; client and server cleanup completed. The real received **52-byte socket** SHA256 was **`5ce69bad20360906eb49ae8fc3c84d3c78ddf34b7e72e66a28ad45452242300e`**.

This is a **graphical compatibility smoke test**, not an explicit visual lighting-difference test. It does not demonstrate original online game-server cooking, inventory, long-running performance, or native owner-Windows rendering.

## Source-safe public GitHub and owner-private release

- `tools/recovery/r303/rebuild_r303_from_pinned.py`: source-only wrapper importing the SHA-pinned original R302 recipe. Exact executed public builder Git blob **`27aaa6420b3bd72a0348ac446673c9933eb8a55a`**.
- `tests/java/r303/R303GroundLightingBorderRegression.java`: genuine real-class RED/GREEN regression source, Git blob **`48f6e3730e6aaf0b7b66a9de8f794c25e45ac40f`**.
- `tests/python/r303/R303SourceSafetyRegression.py`: **18/18** source-only hashing, drift, malformed anchor, output refusal and binary exclusion tests; Git blob **`bbbc1bec0ff617fd0c47919196f9b4e9163dcbff`**. Added to Windows Server 2022 and Ubuntu 24.04 hosted CI; hosted CI does not have private owner game files and does not itself prove client compilation or gameplay.

**Owner-private release** (not pushed as public GitHub binaries): `SpawnPK_v309_R303_GROUND_LIGHTING_BORDER_PRIVATE.zip`, **3,193,475 bytes**, SHA256 **`c5a1b29f9390e8415000d0c6349402ad0fa493b8556128c1ca30addd40716ee7`**, 23 file entries plus manifest (24 ZIP members). Two deterministic byte-identical ZIP builds and **112 independent integrity/evidence checks passed**. Contains the class-only R303 JAR, authored rebuild and Java/Python tests, R302 RED trace, R303 and previous Java regression GREEN traces, three complete rebuild logs, genuine GUI screenshots, local server wire/receipt/timeline and source-only independent verifier. Excludes the original complete game JAR, cache, full source tree, fonts and credentials.

## Acceptance boundaries and next priorities

**Native owner Windows R303 GUI: NOT TESTED.** The older R297 Win32 runner pins R295; its green source-only checks cannot prove R303. Original live server, actual inventory/economy and sustained runtime also NOT TESTED. Keep PR #1142 DRAFT and the user's installed client unchanged. Continue with native R303 graphical evidence or a new real gameplay/rendering defect supported by a failing authentic regression, avoiding redundant preflight-only milestones.
