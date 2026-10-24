# Original v311 R60 — accepted 29-class source-closed renderer-buffer island

**2026-10-22.** Owner-private reconstruction, official original v311 JAR SHA-256:
`5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`.
Original JAR, original and reconstructed classfiles, reconstructed original Java and the original-JAR behavior probe are kept OFF public GitHub.

## Two newly recovered original renderer utility classes

| Original v311 class | Original class SHA-256 | Source-rebuilt Java9 class SHA-256 | Original ordered JVM instruction match |
| --- | --- | --- | ---: |
| `rs/k/c.class` — float buffer | `ccb5d7b4be983b5fec4491dfb3976c25abc6ab09f7d338630e20f080bbd242d9` | `f59fe60ddcd8cf72bd76db4198378763ca8e20d09871e814c6f717d2d796289a` | **92/92** |
| `rs/k/d.class` — integer buffer | `2931d2666e0395455054d06039f97787fc4570d5d217366ddb4040f9525aad57` | `cbb45ef50e982e2d8208fcd09d69fb2e980d9a513f7a33597d9fd547b41a19c1` | **103/103** |
| **Two new** | | | **195/195** |

The two classes use standard `java.nio` direct buffers and have **zero explicit project-class dependencies** of their own. Their selected Java9 source reproduces original class declarations, field/method JVM descriptors, all ordered opcodes, original byte offsets, branch destinations and symbolic method/field operands after normalizing ONLY numeric constant-pool slot indexes. Full original classfile byte equality/attributes are not claimed.

All 27 previously certified owner-private source-island Java files compile with these two sources in **one 29-source, no-stub `javac --release 9 -proc:none -g:none` invocation**, with completely empty original-game compiler classpath and external sourcepath. This produces **exactly 29 original-name classfiles**, and **2,229/2,229 original JVM instructions match**. All 27 previously accepted rebuilt classfile SHA fingerprints remain byte-for-byte unchanged. The private static project-class scanner verified **zero missing explicit original `rs/` references** across the 29 selected classes (constant-pool types and JVM descriptors only, not reflection/assets/native dynamic closure).

## Bounded original-versus-rebuilt behavior and refusal checks

Original JAR and the independently compiled source assembly ran separately under Java 21, exercising the actual `rs/k/c` and `rs/k/d` logic, with the same **22/22 textual behavior transcript lines** for float/int direct and native-order buffer initialization, scalar/bulk writes, flip, clear, growth from 65,536 to 131,072 elements, preserved data, zero and negative reserve operations, and invalid-array bounds exceptions.

A clean extraction of the owner-private archive passed the full verifier. Three deliberate refusals passed: changed Java source without matching SHA, changed buffer resize bytecode **even after repinning both source and compiled classfile SHA fingerprints**, and incorrect original whole-JAR SHA. The original game JAR is never on the compiler classpath or modified. Original-vs-rebuilt behavior equality is bounded, not complete runtime behavior.

Owner-private self-contained archive (never hosted publicly):
`SpawnPK-v311-R60-Renderer-Buffer-29-Class-Private-Sources.zip`
SHA-256 **`0b743bd0ff64934b79f9c5739261658a15059c1105017e95a130bf65622b6519`**.
Contains 29 privately rebuilt original Java sources, manifest, JDK probe, strict verifier, negative tests and README. It contains NO original JAR, original game classfiles, JDK compiled game binaries, game assets or user credentials.

## Correct accepted tally versus still-provisional tile sources

Prior **58 unique accepted original-v311 classes / 3,261 matching original JVM instructions**, across separate source-build records. Addition **2 / 195** gives **60 distinct accepted recovered classes / 3,456 matching original JVM instructions across those records**.

The **largest currently dependency-closed combined source build is 29 original classes / 2,229 instructions** (not a single 60-class build). Independently, the earlier **34 genuine source tile candidate group / 4,160 original instruction matches** still uses **TWO explicitly unaccepted source stubs**: `rs/a/a` and `rs/k/e`. Full-instruction-parity candidate `rs/I` and six other tile classes therefore remain **provisional and excluded from the accepted 60/3,456 total**. Neither renderer source-stub nor full tile closure, complete 1,184-class client, OpenGL rendering, live game acceptance or full binary identity has been solved.

Public hosted [synthetic renderer-buffer source/parity regression](../tests/test_v311_synthetic_renderer_buffers.py) verifies independently authored toy `java.nio` source, exact symbolic instruction parity and fail-closed buffer behavior. It DOES NOT compile the real proprietary source or use the owner's original JAR. Keep PR #1142 **DRAFT / UNMERGED**. No manual gameplay test is required for this source-only checkpoint.
