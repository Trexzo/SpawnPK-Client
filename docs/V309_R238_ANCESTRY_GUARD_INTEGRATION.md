# R238 Lane A — cache R230 ancestry guard integrated

Checked Issue #1117 before modifications. Applied ONLY `src/rs/cache/updater/assets/CacheUpdateTransaction.java` from Lane B cache R230 donor to canonical Lane A R237. Verified exact SHA-256 preimage `d63b3bde561d8603da743482bb539f5992946bd5b513da747bbc0e47be0fafad` and postimage `8ee21c114b98f7ece960b1347609edd8ffce300614f19d7f3103baaeaa715882`. The other 1,276 Java files remain unchanged.

Actual **full private Java11 build**: 1,277 sources, **1,386 JVM .class files, zero compilation errors**. Built client JAR SHA256 `21d3175306dad5a53c4034243ec1fe006330a74f6f423997704c2722fc07bb88`. Complete source ZIP SHA256 `cc726befb7a27da5f9b718c8e0f5a8fef7e28e032296f63980371206010598c4`.

Compiled and ran 11 actual integrated Java regression suites: R230 ancestor collisions **14 passed**, R229 case-sensitive roots **9**, R227 stage mutation **24**, R226 post-rename **23**, R225 witness/space **22**, R224 rollback **21**, R223 inventory **14**, R222 isolation **8**, R221 crash/locking **10**, R220 transaction **8**, and the real cache extractor **PASS** (expected traversal-rejection stack trace in negative test). No production fallback classes substituted.

Consolidated private R238 ZIP `SpawnPK_v309_R238_ANCESTRY_GUARD_INTEGRATED_PRIVATE.zip` SHA256 `79eb2841a7ccf60760c7faa1babe663f9a94b98f3e6da3e135573e57892ff46a` ZIP CRC PASS, including complete Java source, source-built client JAR, exact non-game dependencies, donor changed-only overlay, compiler output, 11 test logs and JSON evidence.

**Limit:** No new R238 GUI startup, local challenge-response, authenticated login, Windows GUI, or gameplay test was performed. Past runtime tests apply to earlier binaries only. Windows-specific filesystem behavior not tested against this private integrated build. Keep draft; Lane B retains cache guard ownership.