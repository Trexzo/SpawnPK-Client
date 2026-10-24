# Original SpawnPK v311 — R103 shader-stage builder and checked-exception parity

**Evidence date:** 2026-10-23. Exact owner-private v311 JAR SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Neither that JAR, privately recovered original-game Java, compiled game classfiles nor genuine third-party vendor binaries are committed to this public repository.

## Two genuinely new source-recovered original classes

| Original JVM class | Original class SHA-256 | Private independent Java9 rebuild SHA-256 | Exact original JVM instructions |
|---|---|---|---:|
| `rs/k/m.class` — shader creation, compilation, link/validate and cleanup | `42baba8580f8ec1aa517b54897e3380b51232939f26cfba2bb7115280246fe19` | `fea3c1551d0edf47646ad467d7718273fd6f1e558bf0489218b3d784cf6c95fc` | **157/157** |
| `rs/k/m$a.class` — nested shader-stage descriptor and accessors | `f386ba0fdd6b48f12268a6a09f7813570d091dde6349411ed335858d27e1da63` | `0f4a0c57a74061d7873471a7bccb8c81db768378bfc7fd2575e21a782c017cac` | **21/21** |
| **Newly accepted** | | | **2 classes / 178 instructions** |

Both original declarations, method descriptors, byte offsets, branches, exception-handler tables and resolved symbolic operands match independently compiled Java9 source after normalizing only numeric constant-pool indexes. Complete original classfile attribute/StackMapTable or byte-for-byte identity is **not** claimed.

The original `rs/k/m.a(rs.k.d.a)` JVM method omits a declared checked exception despite throwing `rs/k/n extends Exception`. Its privately reconstructed Java source declares that exception to satisfy javac, then a strict, bounded transform removes **only that method's compiler-generated Exceptions declaration attribute on a copied classfile**, after checking that it contains exactly the expected `rs/k/n` type. No executable `Code` or handler tables change. The restored full `javap -p -s -c` representation is identical to original. This is not a runtime workaround for broken shader compilation.

## Closed source-generated compilation and deterministic checks

A single `javac --release 9 -proc:none -g:none` invocation compiled **74 previously/newly reconstructed original Java type declarations and one approved javac-generated switch-table donor**. The donor owner is discarded, giving **75 original-named classfiles / 7,509/7,509 original JVM instructions accounted for**. Every one of the previous **73/73 R101 generated classfile SHA fingerprints is unchanged**. The two new classfiles were freshly independently disassembled against the pinned original (178/178 matches), while previous 7,331 instructions retain certification through their identical rebuilt class SHA fingerprints.

The compiler's external binary dependencies are **only actual owner-original-JAR-derived third-party `gnu/trove/` (1,595 classfiles), `com/google/` (2,607) and `org/lwjgl/` (967)**. These private, transient namespace-restricted dependency archives include **ZERO original `rs/` game binaries**, and there are **zero Java implementation source stubs or missing explicit original project-class dependencies**. Existing class/package, enum-member, generated switch-table, Google checked-exception and lambda restorations are preserved unchanged.

A Java reflection probe executed independently against the owner-original JAR and private source-built classfiles with real vendor binaries and matched **40/40 new cases**: shader-stage constructor values, signed integer bounds, null/Unicode source labels, list insertion and ordering, builder fluent identity, instance/static accessor equivalence and missing checked-exception method declaration. **No native GL/OpenGL shader method was called**, no graphics renderer/game client was launched, and R101's earlier behavior cases were not rerun.

## Clean archive replay and failure-path evidence

Private self-verifying ZIP: `SpawnPK-v311-R103-Shader-Pipeline-75-Class-Private-Sources.zip`, SHA-256 **`00d2fbf760c34b3de82541f9319b0a6116ed413a9dc74b726ff00d53f9138e29`**, size 167,923 bytes, 115 entries containing **75 canonical owner-private Java sources** and verifier/probe/manifests. It contains **NO original game JAR, any compiled game or vendor classfile binaries, original vendor archives, credentials, fonts or game assets**. Never upload the recovered-source ZIP to public GitHub.

The ZIP was independently extracted and successfully repeated the full class/source/vendor SHA verification, 75-class Java9 compilation, 73 unchanged fingerprints, 178 new instruction comparisons and 40 original-vs-rebuilt behavior cases. **Eight/eight deliberate invalid tests failed closed from clean extraction:** altered source; deleted source; wrong original-JAR hash; forged LWJGL vendor-class hash; unauthorized existing game class/package alias; modified vendor extraction tool; modified compiler-only checked-exception restoration tool; and modified original JVM instructions **after repinning both reconstructed source and newly compiled class hashes**.

## Audited class count, scope and remaining blockers

R101 accepted 101 distinct original classes / 8,527 matched original JVM instructions cumulatively across **separate accepted source builds**. R103 adds two newly accepted classes / 178 instructions: **103 distinct original v311 classes / 8,705 cumulative matching original instructions**. The **largest single dependency-closed source-generated output is 75 original JVM classfiles / 7,509 instructions**, **NOT** a simultaneous 103-source build.

[Independent toy Java9 checked-exception metadata tool](../src/spk_recovery/checked_exception_identity.py) and [synthetic-only original-versus-corrected JDK bytecode tests](../tests/test_v311_synthetic_stage_exception_restoration.py) contain no private game Java or binary classes; hosted CI checks these toy regressions, not the owner-private full 75-class proof.

The substantial original `rs/k/k` OpenCL class, the `rs/k/e` full renderer, the `rs/a/a` scene model, and seven previously provisional tile source candidates remain unrecovered. Shader creation/linking has **not** been executed on a real GPU. No whole-original-client source release, full classfile identity, native graphics/runtime, login or gameplay acceptance is claimed. Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**.
