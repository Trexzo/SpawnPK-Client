# SpawnPK v309 R306 — live draw-radius transitions

**2026-10-20. Actual original-client runtime defect fixed.** PR #1142 remains DRAFT; no merge or owner installation. Private original source, full game JAR and cache remain outside public GitHub.

## Reproduction and production fix

The real compiled R305 Scene class crashes after a live draw-radius change without a viewport resize. The source-owned zoom setting invokes Scene.method381, updating activeDrawDistance without guaranteeing a call to Client.alignViewport. A real test initialized a 51x51 viewport at radius 25, changed the active radius to 50, placed an actual Tile at (74,50), and called Scene.drawScene. **R305 RED:** ArrayIndexOutOfBoundsException, Index 74 out of bounds for length 51.

R306 corrects Scene.drawScene in two places: (1) before GPU or software rendering, if the stored visibility grid no longer matches 2*activeDrawDistance+1, recalculate it using the original setViewport with the retained viewport dimensions; (2) use a bounds-checked per-tile visibility accessor, returning false outside the current radius instead of indexing past it when software traversal is wider than the configured radius. An unchanged subsequent frame reuses the same visibility array; there is no unconditional per-frame rebuild.

Exactly one original production source changed: Scene.java SHA256 R305 **dd02b8627053d7a9dc1c6f932cb34c5e78c4c5d21103a06ca169199f8b49f17e** to R306 **b8fa016278c1ef8def2866dbffd54bf3a78f7b3bb28985672e1609e7f6787a3d**. No packet, asset, item, authentication or live-server logic changed.

## Genuine Java and GUI evidence

Three independent full Java 11-target builds, each **1,277 original sources -> 1,386 classes**, produced byte-identical R306 class-only JAR SHA256 **9db9e6f3b43fc894f2e62828a67c04b00d22292d5782c9b967e3da6be3c35b14**. Only rs/Scene.class changed from R305; the other 1,385 classes are identical. The third build used the exact public SHA-pinned R306 wrapper instead of an exploratory private build script.

R305 RED / R306 **64/64 GREEN** compiled-client tests exercise repeated radius transitions 25->50->10->1->25->50->25->5->30->10, grid resizing, viewport geometry preservation, no redundant recalculation, and exclusion of out-of-radius tiles. All earlier R293–R305 real-client suites were rerun against R306: **106,447/106,447 PASS**, including the independent R305 102,510-cell yaw/edge reference with zero mismatches. **Combined total: 106,511/106,511 PASS.** The public 18-case R306 source-only suite passed locally and in GitHub Windows Server 2022 and Ubuntu 24.04 hosted CI.

An actual Linux/Xvfb 1400x900 reconstructed GUI test used the exact R306 JAR with an isolated copy of an already SHA-verified original cache home. **Outer exit 0**, original OSRS region **13386/field1134** genuinely rendered (98.52% nonblack viewport crop). Java Robot selected **Cook** on range object ID114; the isolated localhost mock server received an ISAAC-decoded outgoing **opcode132 / length6 / world tile(3362,4769)** and returned matching synthetic **opcode253** acknowledgment. Actual received wire **51 bytes**, SHA256 **45d893ebbbb12e506a08dbe249f5c19ae9d203747124747a564c9c4e24e25a54**. Child processes cleaned up.

This is a real graphical compatibility smoke test, not native Windows or original authenticated live game server gameplay.

## GitHub source-safe provenance

- tools/recovery/r306/rebuild_r306_from_pinned.py — Git blob 6342da46526428002d61586a12022d44d9e210b6. Checks unchanged R305 public builder, original private R278/R265 archive SHA pins, exact R305 source preimage, exact R306 postimage and final class-only binary SHA; rejects existing output.
- tests/java/r306/R306DrawRadiusTransitionRegression.java — Git blob 85110e48ce69573addd78305a58f56dfa90807dd. Byte-identical to actual compiled R305 RED / R306 64-case GREEN regression.
- tests/python/r306/R306SourceSafetyRegression.py — Git blob dca06cd247596d463773bb3138d4ae5c1da1070e; **18/18 PASS** in local tests and hosted Windows/Linux source-only CI.
- docs/V309_R306_REAL_DRAW_RADIUS_TRANSITION_AND_GUI.md — this record. Hosted CI contains no private game JAR/cache, so it must not be described as native GUI evidence.

## Private release and remaining gate

**SpawnPK_v309_R306_LIVE_RADIUS_TRANSITION_PRIVATE.zip** — 3,192,697 bytes, SHA256 **afaf1192533972f9a728ef466b3d8c49d95fda0bbf2cd4680070a6d94e4a8711**, 26 ZIP entries. Two independent deterministic ZIP builds were byte-identical; an independent verifier passed **163 checks** over source/build hashes, 1,386-class JAR, one-class diff, R305 failure and R306 Java pass logs, screenshots, actual socket bytes and synthetic ack. It contains the private class-only JAR and authored test/rebuild/evidence files, but **not** the original full client, recovered Java source tree, original cache, fonts or credentials. Do not publish that private ZIP or its original game screenshots publicly.

**Native owner Windows R306 GUI: NOT TESTED. Native GPU radius-50 visual output: NOT TESTED. Original authenticated server cooking/inventory and sustained gameplay: NOT TESTED.** JVM radius transitions and calculations are tested. The older owner Windows launcher R297 pins R295 and cannot prove R306 acceptance. Keep PR DRAFT and owner-installed files/main unchanged. Next milestone should be a native owner Windows/GPU graphical acceptance, not another redundant preflight-only layer.
