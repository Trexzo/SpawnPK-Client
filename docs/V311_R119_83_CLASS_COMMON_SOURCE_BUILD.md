# Original SpawnPK v311 R119 — 83-class integrated Java9 source build

**Private original binary authority:** owner-v311 `client(20261021-111920).jar`, SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. All owner-private reconstructed Java, original game/vendor binaries and behavioral verifier stay **OFF public GitHub**.

## Integration only — no newly recovered distinct original JVM class

R119 promotes three **previously accepted R114** enums to the already-verified R118 80-output source compilation. The new **ONE Java9 compiler invocation** produces **83 original-named classfiles / 8,569 accounted matching original JVM instructions**. All **80/80 R118 rebuilt class SHA256 fingerprints are byte-for-byte unchanged** (78 original R106 source group, R117 scene node and R118 nested renderer enum).

| Added already-accepted original class | Original symbolic ordered JVM instruction parity | Integrated rebuilt class SHA256 |
| --- | ---: | --- |
| `rs/l/f/a/a/e.class` | 50/50 | `ed0fd12131f563fcbf68c2db75b584af27034a057728b4d0ceb702c04e548829` |
| `rs/l/f/a/f/b.class` | 40/40 | `57736fa828129010fca85ec3bd3e04a0790e68d18908e3211cc67099dc72db04` |
| `rs/l/f/a/i/g.class` | 80/80 | `6b8d3080b88475825ddf2f5ded8bb836b20e273b847ac65eb9cf3bd4a553b3fc` |
| **Three existing types integrated** | **170/170** | All identical to accepted R114 hashes |

**Accurate accepted cumulative ledger UNCHANGED:** **116/1,184 DISTINCT original v311 class identities / 10,038 matching JVM instructions ACROSS SEPARATE original source-island builds**. R119 adds **ZERO newly accepted distinct original identities and ZERO newly counted original instructions**. Largest single original-named build rises R118 **80/8,399** → R119 **83/8,569**, not 116 compiled together.

### New reviewed class/package collision alias

Previously accepted original enum **`rs/l/f/a.class`** has canonical Java type **`rs.l.f.a`**, which conflicts with new package prefixes `rs.l.f.a.a`, `rs.l.f.a.f`, `rs.l.f.a.i` in the three existing R114 Java source files. R119 temporarily stages that prior stage enum as `rs/l/f/RecoveredSceneStageV311` by renaming only its own Java declaration/constructors. After one common `javac --release 9 -proc:none -g:none` build, the alias is inverse-restored in the copied compiled classfile constant-pool JVM type metadata **without modifying executable `Code` or catch-handler instructions**. The restored prior enum and all other 79 old outputs retain their exact R118 compiled SHA hashes. Original Java source files are unchanged.

The earlier reviewed temporary compiler aliases remain: `rs/a` scene node class vs package `rs.a.*` (R117) and the **disposable** synthetic donor outer `rs/k/e.class` producing the previously recovered nested enum `rs/k/e$a` (R118). That temporary outer classfile is discarded, **NOT treated as authentic recovered original renderer source**. Actual compiler dependencies contain only the exact original-JAR-derived authenticated **vendor-only** Trove (1,595 classes), Google (2,607) and LWJGL (967) classes, **zero original `rs/` game binary classfiles**, zero retained fake project source implementation stubs.

### Private original JAR verification and limitations

The owner-private ZIP `SpawnPK-v311-R119-83-Class-Private-Integrated-Sources.zip` was independently **fresh-extracted**, then recompiled/reverified against the same exact owner original v311 JAR. Archive **SHA256 `f686842b72c0c752139e6c0e06d97ff71369abc6a6a20cf164a5779b54ad2c1a`**, **264,006 bytes / 159 ZIP entries**, contains reconstructed Java, manifest, probes and verifier, **NO original JAR, compiled game/vendor `.class`/`.jar`, assets or credentials** and is **not uploaded publicly**.

Strict verification checks exact 83 inputs and 83 original-name outputs, all SHA-pinned previous original/rebuilt/source identities, original-vs-built `javap -p -s -c` symbolic declarations/offsets/instructions **170/170** for the three newly integrated (not newly discovered) R114 enums, and preserves **80/80 previously accepted rebuilt SHA hashes**. In addition:

- Original JAR vs rebuilt headless new UI enum probe: **20/20 outputs match without original-game runtime fallback**.
- Original JAR vs rebuilt linked scene-node probe: **24/24 outputs match without original-game runtime fallback**.
- Original JAR vs rebuilt previously accepted renderer-enum/node probe: **17/17 outputs match, requiring the original JAR as trailing *RUNTIME-ONLY* fallback for the unrecovered outer renderer `rs/k/e` reflection metadata**; the original JAR is never provided to `javac`.
- Freshly extracted negative suite **9/9 rejected**: edited source, missing source, extra fake source, tampered compiler, tampered probe, inflated distinct cumulative ledger, inflated combined-output ledger, incorrect R118 baseline hash, and **actual enum constant reordering after SHA-256 pins for both the changed Java source and changed compiled class were refreshed**; original JVM instruction parity still fails. The last test restores the canonical Java source through a guaranteed `finally` block.

Hosted public [synthetic Java9 class/package enum collision test](../tests/test_v311_synthetic_stage_enum_package_alias.py) uses only invented toy Java fixtures. It checks repeatability, prior-compiler output stability, restored classfile metadata and true altered JVM code detection. **Public CI cannot reproduce private original-JAR comparisons and must be tracked separately.**

### Remaining blockers

The complete original `rs/k/e` renderer (17/36 accepted direct dependencies) and `rs/a/a` scene model (5/14 accepted direct dependencies), seven provisional tile classes, whole game client source-build, original bit-identical classfiles, native/GPU renderer and gameplay are **NOT accepted/verified**. An accepted selected compiler output set does not imply full project runtime/static closure while `rs/k/e` outer metadata remains unavailable.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**; no manual gameplay test is appropriate for R119's source-only integration.
