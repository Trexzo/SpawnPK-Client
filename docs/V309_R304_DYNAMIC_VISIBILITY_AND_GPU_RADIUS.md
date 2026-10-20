# SpawnPK v309 R304 - Dynamic scene visibility and occluders

**20 October 2026.** Actual recovered Java client renderer fix. PR #1142 remains DRAFT; nothing merged or installed. No complete recovered game source, original client JAR, cache, fonts or credentials in public GitHub.

## Reproduced source defect

The genuine R303 client threw ArrayIndexOutOfBoundsException when Scene.setViewport was called with activeDrawDistance 1, 10, 15 or 24, because the viewport grid was sized according to the active radius but its scan still iterated hard-coded coordinates -26 through 26. For example, actual R303 RED at radius 1: Index -24 out of bounds for length 5. Larger radii, including GPU radius 50, still relied on the fixed 51x51 visibility table and occluder clipping.

## One-class production correction

- Scene.setViewport now sizes the stored and temporary visibility grids for the actual active radius and scans the matching radius rather than hard-coded -26..26.
- Radii 1..50 are exercised with genuine Java Scene instances; invalid/extreme radius settings fall back to the original 25.
- Scene.method56 occluder visibility now uses the active radius and actual visibility array bounds instead of fixed center 25 and clip limit 50.
- Existing 25-tile behavior and previous R290–R303 source fixes retained; no opcodes, original scene objects or network endpoints changed.

Scene.java SHA256 original R303 preimage: ee0660154ab0e289448194a476fc6b2629ea83e1d99ba7477755e6f4885f93b6.
R304 postimage SHA256: 839492e3d66ea546699f18338f09135e9787ff0c40ef193517cb18e68f8accd4.

## Actual verification

- Full SHA-pinned original R278/R265 owner inputs, 1,277 recovered Java sources compiled to 1,386 Java11-target classes TWICE independently.
- Both deterministic class-only JARs SHA256 1364d7be33147b5dbe9437f2222007402db449f9b1e4a244565680b608385f20. Exactly rs/Scene.class changed from the R303 JAR; other 1,385 classes byte-identical.
- Real R303 RED / R304 GREEN, 621/621 new viewport/occluder JVM cases: supported radius 1..50, invalid radius fallback, repeated resizing and occluders at edge of small and extended ranges.
- Previous R303 through R293 genuine real-class suites 3,316/3,316 PASS against R304; COMBINED 3,937/3,937 assertions.
- Authentic-cache local Linux/Xvfb GUI replay outer process exit 0: region13386/field1134 rendered at 1400x900, AWT Robot Cook range114, genuine local ISAAC-decoded outbound opcode132 length6 world(3362,4769), paired synthetic localhost opcode253 response. 51-byte wire SHA256 d208230b86a240045afac6b587f82f72cd0be47b099775b45a4cdfa37be95f5b. Child server and client terminated.
- This GUI replay used an isolated previously SHA-verified cache home, not a fresh archive intake, and did not test native GPU mode or real online server.

## Public GitHub source-only files

- tools/recovery/r304/rebuild_r304_from_pinned.py - Git blob 2c1ef85434c965845f5ed4c4cebfab4c72ac5e1f, byte-identical to twice-executed builder. Requires unchanged exact R303 public recipe and source/compiled-output hashes; refuses existing output.
- tests/java/r304/R304VisibilityDistanceRegression.java - Git blob 4bd7c8b8641595dbb7e7316d0cf307d6f351e1ea, exact authentic 621-case RED/GREEN regression source.
- tests/python/r304/R304SourceSafetyRegression.py - Git blob 484f654421252acc744026cc0ae6bb32fc951ff0, 16/16 source-only tests added to Ubuntu24/Windows2022 CI.
- Source-only CI does NOT contain private game jars or cache. Do not equate its result to runtime rendering verification.

## Owner-private deliverable, not published publicly

SpawnPK_v309_R304_DYNAMIC_VISIBILITY_RADIUS_PRIVATE.zip, 2,979,533 bytes. SHA256 34561ba943443e3df2fb49ac1d4f86d046211c16f62cb09786027d4c26a638c2. Two independent deterministic ZIP builds byte-identical, 23 members, independent 109-check manifest/CRC/SHA/JAR/screenshot/socket verifier PASS. Contains privately rebuilt class-only JAR, public-safe build/test recipes and real Java/GUI evidence. Excludes original complete game client, original cache, recovered complete Java source, fonts and credentials.

## Outstanding acceptance

Native owner Windows R304 GUI: NOT TESTED. Native GPU-specific 50-tile visual output: NOT TESTED; JVM viewport/occluder calculations are tested. Original authenticated server inventory and sustained online gameplay: NOT TESTED. Existing owner Windows R297 runner pins older R295 and is not R304 acceptance evidence. Keep PR #1142 DRAFT, main and installed owner files unchanged.
