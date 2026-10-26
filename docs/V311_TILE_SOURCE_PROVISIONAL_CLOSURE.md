# Original v311 scene-tile source frontier — six provisional Java source candidates

**Date:** 2026-10-22. **Status: PRIVATE VERIFIED, NOT ACCEPTED INTO RECOVERED CLASS TOTAL.** Original game JAR, reconstructed proprietary Java, compiler outputs, and private probes are NOT published to GitHub.

## Original binary authority

The sole original authority is owner-provided `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`.

Original class | Original class SHA256 | Independent Java9-rebuilt SHA256 | Original JVM instruction parity
--- | --- | --- | ---:
`rs/H.class` | `ae42657b2cf14f40ce4966d77a714734d4b9ac73560dfd1753fed213f78c6d7a` | `7e2795c9135ecf903b454f7a2cee97900dd9f8f675e1536a7dd415489cdea1f8` | 56/56
`rs/T.class` | `5ff3223a6bc48ec9c7ba68034d8adb350a58f661db4f88cec7c8c7782e2c884e` | `546b60b390e3cdeecc607aaebf58d056760a391fc97b548c9bdd7aca376fcc14` | 6/6
`rs/U.class` | `17072aba664c89498e25041bbf51fb287fb0201215271b06596e8aedb7ecfa32` | `cb64493f6b735023f1e953e70786f701997ddf8739eda9fceec1676c41223f64` | 9/9
`rs/l.class` | `e633197b4bcd658e5b75e239937bab99241578957027a0694cb1f18480dc247d` | `508078f2e717b6d4715c0a9b4224f51778da7cbd52640ea5c390d984a437a20f` | 6/6
`rs/m.class` | `c05f2d5661a8c554d7f20e1e0f816e6f138c7b24bc185ec8815c805e66884f9d` | `acf370f684117a73b221f33a8221285c2c0b1d303020694f81d990f73dc0eaac` | 6/6
`rs/n.class` | `47d084fedbd212af8d3d8622fe894b476de6e911b3a88a50b3a87a92dbaa0cf7` | `1f81af7235a355866672641fa0ee2fb611f855aae9e128833461b02505ac6c34` | 3/3
**All six provisional source candidates** | | | **86/86**

Each candidate matches the exact original-name class declarations, ordered JVM byte offsets/opcodes/branches and symbolic field/method operands after only normalizing numeric constant-pool indexes. All classfiles are compiled at Java9 target (major 53). Complete classfile binary identity, generic program equivalence, and source-text identity are not claimed.

## Dependency boundary — essential non-promotion rule

This experiment compiled the **27 already certified owner-private source classes plus six provisional source candidates** in one Java9 `javac --release 9 -proc:none -g:none` invocation. It also compiled **two declaration-only SOURCE STUBS** to represent the *unrecovered* original types `rs/I.class` and `rs/a/a.class` (35 emitted JVM classfiles total, of which only 33 represent reconstructed source). No original client binary was on the compiler classpath or sourcepath, but **this does NOT establish independent full project source closure**. The two stubs are deliberately marked non-recovered and must never be counted as original rebuilt Java sources.

- Original `rs/H` had six direct original-`rs/` type dependencies missing from the previous 27-source island: `rs/I`, `rs/T`, `rs/U`, `rs/l`, `rs/m`, and `rs/n`. Of these, five now have exact source-to-bytecode candidate parity; `rs/I` remains an unimplemented dependency.
- The provisional `rs/T`, `rs/U`, `rs/l`, `rs/m`, and `rs/n` classes all also refer to original `rs/a/a`, which is **not** source-recovered. `rs/a/a` itself extends original `rs/a` and references other original project classes. Original `rs/I` also references `rs/k/e` in a getter. Both missing sources have further transitive work.
- Existing 27 classes produced exactly their previously certified SHA256 compiler fingerprints, unchanged by compiling with the additional sources.

The independent private original-JAR-vs-rebuilt-Java `SceneTileProbe` yielded **12/12 identical behavior transcript lines**, checking constructor coordinates (including negatives), fixed five-slot arrays, default flags, typed linked-node and scene record state, entity links and accessors. The private verifier independently checked every selected original class SHA, source and rebuilt class SHA, exact compiler output set, all source disassemblies, and a deliberate changed-`rs/H` source was correctly rejected.

**Accepted cumulative original-v311 source evidence remains 58 distinct classes / 3,261 original JVM instructions**, across separate builds. The six classes / 86 instructions above are **provisional and are not included**. No authentic full-`rs/H` dependency-closed Java9 compilation, original classfile-byte identity, full scene renderer `rs/V`, gameplay launch or online client acceptance is claimed.

The owner-private handoff bundle (not hosted in GitHub) is `SpawnPK-v311-R58-Tile-Frontier-33-Source-Provisional.zip`, SHA256 `cb7e0fae1f87eeb050732b1b217183b4c4cd416422aebc44480b8cb34f8c6a16`. It contains 33 authentic reconstructed source files (27 accepted, six provisional), two visibly marked SOURCE STUBS, an exact hash/classfile manifest, the private 12-case probe, and a fail-closed verifier; no original client JAR, assets or compiled classfiles.

**Next gate:** independently source-build `rs/I`, `rs/a/a` and their transitive dependencies, remove the two declaration-only stubs, compile/verify the full tile source island from original-name Java alone, then independently promote source-recovered status. PR #1142 stays DRAFT and UNMERGED; no manual gameplay test is appropriate for this source-only milestone.
