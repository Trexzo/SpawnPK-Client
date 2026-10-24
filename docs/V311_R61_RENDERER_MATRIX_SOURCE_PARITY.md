# Original SpawnPK v311 R61 — 32-class renderer matrix source island

**Audit date: 2026-10-23.** This report records owner-private source recovery from the exact original uploaded `client(20261021-111920).jar` with SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The original JAR, independent recovered proprietary Java, original classfiles and runtime probes are **not** committed to this public repository.

## Authentic original Java9 source reconstruction

| Original v311 class | SHA-256 of original class | SHA-256 of independently rebuilt Java9 class | Ordered original JVM instructions |
| --- | --- | --- | ---: |
| `rs/k/h.class` — float 4×4 renderer matrices | `6345fb40fa195446f9e0888b8a0ec16a33d4ad34d32f66e8c943606b7e0fc441` | `d8615bae1cc6d802930f5335c34cf1413308dcbee07a761978d4d9764a66680c` | **850/850 NEW** |
| `rs/k/a.class` — renderer metadata holder, previously recovered | `e47b1cdcfde0e318b0dafcec9c25b88d9c9f305555d888c95e5f9c1dc0da0281` | `9aadf0ccd261d24b5b14bf77fb23400cd609acdfbde9e450b9e2e709bfee4060` | **15/15, ALREADY COUNTED** |
| `rs/k/n.class` — renderer exception, previously recovered | `ed7388e0f0095e24548d0f97afb4038d9eb1bb73f1284b86450a8a54ee2a3555` | `c8dc9253f15b0f323a624dbf3803f2737331599d5a717e94192f3fcc700504a7` | **4/4, ALREADY COUNTED** |

The original `rs/k/h` code includes six separate constructors/factories for identity, scale, translation, X/Y rotations and projection matrices, plus unrolled in-place 4×4 matrix multiplication. It has **zero original game-project class dependencies** beyond itself. Its 850 original instructions, original offsets, branch targets, resolved symbolic constant operands, method signatures and class declarations **exactly match** independently compiled original-name Java source; only numeric constant-pool indexes were normalized. Full original classfile SHA identity is **not claimed**.

The previous fully source-closed 29-class R60 source island and all three classes above compiled together in **one `javac --release 9 -proc:none -g:none` invocation**, with an **empty original game binary classpath and external sourcepath**. Exactly **32 source-backed Java9 classfiles** were generated; there are **no declaration-only source stubs** and **zero unresolved explicit original project-class references**. Every prior R60 private compiled class SHA fingerprint remained unchanged (**29/29**). All **3,098/3,098 ordered original JVM instructions** across this combined compilation match.

**Accurate cumulative distinct-class accounting:** R60 accepted original-v311 tally was **60 distinct classes / 3,456 matching instructions** across separate source-builds. `rs/k/a` and `rs/k/n` had already been accepted in the original first-3 and 23-class milestones, so they **must not be counted again**. Only `rs/k/h` adds **1 class / 850 instructions**, resulting in **61 distinct accepted original v311 classes / 4,306 original matching instructions**, accumulated across separate accepted build records. Do not describe this as a single 61-class compilation.

## Original-versus-rebuilt behavior and negative tests

The independent owner-private JDK-only probe compared **39/39 exact original-versus-rebuilt transcript cases** for metadata and exception construction, identity, scale, translation, rotation, projection matrices, float raw-bit results including ±0, NaNs and infinities, multiply order, aliased matrix inputs and invalid-array exceptions. Previously accepted float/int direct-buffer probes still matched **22/22** cases. The probe does not launch the client, exercise OpenGL, validate scene drawing or access accounts.

Re-extraction of the owner-private archive and its independent strict verifier passed all original/class/source/compiled SHA pins, Java9 compiler inventory, exact symbolic original disassemblies, full explicit selected-project dependency closure, old behavior probes and new 39-case probe. **Three deliberate refusal tests** passed: mutated source hash; a changed matrix formula correctly refused at original JVM instruction parity **even after repinning source and compiled SHA values**; and a wrong original JAR SHA refused.

The owner-private self-contained archive (not distributed on public GitHub) is `SpawnPK-v311-R61-Renderer-Matrix-32-Class-Private-Sources.zip`, **SHA-256 `09fe7e91c15ef58aec4e470846a39d7845cefa31f18d1a847f3c35bc2669f07e`**. It includes 32 owner-private source files, exact SHA manifest, owner-private reproducible verifier and probes, refusal tests and README; it excludes original binaries, compiled game classes, fonts, credentials and game assets.

Public [synthetic-only Java9 matrix dependency/regression tests](../tests/test_v311_synthetic_renderer_matrix_parity.py) compile unrelated toy classes and exercise class closure, symbolic instruction equality, original-versus-rebuilt toy computations and malformed input/mutation refusals. Hosted CI **does not** have the user-provided original JAR, recovered source or private proof material.

## Limits and next objective

The larger `rs/I` tile-source group remains **provisional** despite its exact 2,040 JVM instruction match and 468 bounded constructor comparisons: it still uses two **unrecovered declaration-only stubs**, `rs/a/a` and `rs/k/e`. These have large direct/transitive dependency graphs and are not replaced by recovering renderer matrix primitives. Authentic full `rs/H` and `rs/V` source closure, all 1,184 original client classes, classfile binary identity, graphics/server acceptance and in-game behavior are not claimed.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT / UNMERGED**. Continue dependency-closed renderer support source islands and original scene dependencies; manual gameplay verification is not warranted at this source-only milestone.
