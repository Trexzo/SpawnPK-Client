# R179 — complete original-v309 Packet Java method and initializer reconstruction

This is original SpawnPK **client-only** recovery. Stacked on [R178 #1069](https://github.com/Trexzo/SpawnPK-Client/pull/1069). Original-derived Java/JAR bytes are PRIVATE and not committed to public GitHub.

## Actual original v309 class-level method recovery

The original SHA-pinned JVM owner `rs/x/e.class` (SHA-256 `b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2`) is independently reconstructed as an original-named Java9 source file. It extends two separately and completely reconstructed original source classes `rs/a` and `rs/t` (R177).

| Strict original-v309 JVM source comparison | Measured result |
| --- | ---: |
| Original ordinary methods (including constructors) | **80 / 80** |
| Original static initializer `<clinit>` | **1 / 1** |
| Matching original ordinary-method JVM instructions | **2,144 / 2,144** |
| Matching original static-initializer JVM instructions | **152 / 152** |
| **Combined original JVM instruction equivalence** | **2,296 / 2,296** |
| Original classfile Java major | 53 (Java9), matching |
| Original field name/type/access identities | **11 / 11** |

All original/recompiled 80 ordinary method bodies match method descriptors, access flags, max stack and local slots, argument counts, original instruction offsets, operations, branches and resolved original JVM class/member/constant targets. The 152-instruction static initializer matches including BigInteger constant creation, original 33-entry bitmask array data and the original `rs/h` instantiation. The complete field and method inventories and superclass identities match. Original Java code preservation here is **method Code parity, not byte-identical full classfile parity**; auxiliary source implementations, StackMap/class attributes and full runtime compatibility are distinct gates.

The original-v309 full JAR SHA256 is `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

Private SHA-pinned results:
- **Complete original Packet Java source ZIP:** `595d337e028004aeeb9fbcb46962794c3f1f5c809feb8e5a5ccb377f25414cac`
- Private source-only compilation helper ZIP: `88111b9b85e82b99715928612bd7e22aa0e20e9f5c41e58f015f1f0325b9f876`
- Private full 81-JVM-member original-vs-rebuilt proof JSON: `848ae63ff2e8151d76bb023c6e73f0bf836ad599ab7410cf90c2775338e107c1`

The source builds privately with original `rs/t.java`, `rs/a.java` and four strictly separated compilation-only Java type sources (`rs/q/a`, `rs/v/a`, `rs/h`, `rs/f/a`). These four types have exact original JVM owner names and required signatures, but **their placeholder implementations are not evidenced as original**. Original game/client binaries were not used as a fallback javac classpath.

## Full-source compiler measurement

A new PRIVATE `recovered-source/v309/src/` candidate ZIP contains **1,279 Java files**: 1,278 prior candidate Java file contents preserved byte-for-byte plus the recovered complete original Packet source. Its SHA256 is `b195895ba98e3b2c34bc638487eb34311e85687c64fb002ee9de6c60a9dd740f`. **None of the four provisional helper sources is in this canonical candidate**.

Controlled JDK21 `javac --release 9 -g:none -proc:none -implicit:none` with empty external/original binary classpath, all Java sources explicitly compiled, up to 10,000 diagnostics:

| Candidate | Errors |
| --- | ---: |
| 1,278 Java files, before Packet | 2,339 |
| 1,279 Java files, after Packet | **2,343** |
| Net change | **+4** |

This is **not a compiler error reduction**. The difference consists of **six new diagnostics** (missing source helper dependencies, plus a type mismatch with an existing decompiled-source class) and **two resolved missing-`rs/x/e` diagnostics**. The old provisional binary-capsule 516-error frontier was a different compiler setup and is not comparable.

- Private new whole-source javac delta proof JSON SHA256: `5bb874b86d09d1c10a5fdf113f619043cfa38a115c8cdd9593a20955b585fb7f`.
- The four missing dependency owners require independently recovered source and/or original-evidenced mappings before the whole client can compile cleanly. **Do not publish the compilation-only helper implementations as original source.**

## GitHub verifier and completion boundary

R179 adds an exact-SHA-pinned private verifier that requires R177's two complete original parent class proofs first; builds a complete Packet Java class from source with only four explicit type-only helper Java sources; checks original class/super/method/field identities, classfile release and all 81 JVM Code streams / 2,296 decoded original instructions. It compares original versus rebuilt method Code, not placeholder helper behavior. The verifier reports full client compilation and derived-source redistribution permission as false.

Synthetic Ubuntu/Windows CI uses a separately created non-SpawnPK Java class with original-style parent hierarchy, constructor and static initializer, plus a deliberately different source-only helper implementation. Changed code, mutated static initializer, wrong source SHA, expected method count and instruction count must be rejected. R178 tests rerun. Public CI does not contain the original Java source, RSA constants or original binary files.

**Next priorities:** recover the four source-only dependency implementations; reconcile existing source-type collisions/aliases, rerun the normalized dependency classpath whole-source compiler, then test classfile attributes, runtime interoperability and networking. Restoring the full Packet class's method bytecode does **not** mean the entire v309 client is recovered or playable, and original-source publication rights remain unresolved.
