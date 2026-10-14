# R161 — reconstruct both original v309 Packet-dependent matrix Java methods

Scope: SpawnPK **client-only** original-derived Java recovery. Stacked on [R160 #1051](https://github.com/Trexzo/SpawnPK-Client/pull/1051); milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). No original client code, original .class bytes, private Java source or helper ZIP is distributed through this public repository.

## Exact original-v309 private recovery

The last two original matrix JVM methods have independently reconstructed Java implementations:

| Original method | Function | Matching original/recompiled instructions |
| --- | --- | ---: |
| public constructor b(rs/x/e, boolean) | Allocate 16 float matrix entries; delegate to matrix decoder | **11/11** |
| package-private a(rs/x/e, boolean) | Decode the transform branch or read 16 raw floats | **50/50** |
| **New R161 methods** | | **61/61** |

The loader's flag-controlled transform branch builds the original transform helper, invokes original Packet B():int **six times**, performs the three signed-short decode conversions through original helper class d.a(int):float, applies the transform's setters and calls the separately reconstructed matrix component writer. The alternate branch loops sixteen times, invoking original Packet s():float for each array entry. An actual **private** Java9 javac source-only rebuild reproduces *all* original JVM opcodes, offsets, branch targets and resolved original class/member operand references across both methods, without any original game Packet classfile on the compiler classpath.

This result is **narrowly matrix-method instruction parity**, not proof of original Packet internals. The temporary Java-only rs/x/e source provides exactly the B():int and s():float signatures, with **unverified placeholder bodies**. Other helpers, including transform setters and signed-short converter, also have compilation-only source bodies. No original game classfile is executed or linked for compiler dependencies. R149 independently verified the **signed 16-bit instruction body** against two decompiled Packet candidates, but could not uniquely identify which original source method name corresponds to B. The loader's six B calls thus retain the original binary method identity and DO NOT resolve that ambiguity.

The original matrix class com/a/b/a/b.class is SHA-256 **52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030** within the original v309 full client SHA-256 **ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38**.

## Actual private source build

The private 11-method original-name Java source compiled with five entirely Java-source-only helper owners: com/a/b/a/a, com/a/b/a/c, com/a/b/a/d, com/a/b/a/e and rs/x/e. No original .class files were present on its javac classpath, and no private loader or helper implementation was run. In that *one* combined source-only class, the nine earlier R159–R160 methods (3,369 original instruction matches) plus both R161 methods (61) matched **3,430/3,430 original JVM instructions**.

Private exact source snapshots:
- Private 11-method matrix source ZIP SHA-256: **06b80a7de8210a70796fac5757fc67e43de15d46de0cefd6a97364f08d9c9b48**.
- Private five-helper Java source ZIP SHA-256: **d5a346413ceee1a0a657923df9750a80beb31be933ff708415621b7d812e3c3e**.
- Private 11-method selection JSON SHA-256: **e3fe0908fbd0cda090453531a282befd65c8190d4f8f17448e6fe41885773101**.

## New independent GitHub verification gate

R161 adds a separate private original-JAR vs Java-source verifier, rather than weakening R156's ban on unapproved rs/ scaffolds. It allows **exactly one** original rs/ Java-only type under an explicit original JVM class identity and validates all other helper source identities against original classfiles in the pinned original JAR. It requires:
- Complete original JAR, exact matrix Java owner ZIP, helper-only Java ZIP and explicit method allowlist independently SHA-pinned.
- Original non-rs matrix owner provably in R136's original game-linked binary exclusion partition.
- Selected original Packet constructor **and** loader plus all directly selected same-owner call dependencies; original and independently compiled method Code must match in decoded instructions, branch offsets, resolved members, code lengths, max stack/locals and exception handlers.
- No JVM generated classes other than the exact original named Java compilation units, and no original game-binary or external binary fallback.

By default the real-v309 private verifier expects 11 selected method identities, **3,430 matching JVM instructions**, five Java-only helper classes and **five closed matrix self-call edges**. The resulting sanitized private report explicitly vetoes original Packet/helper source-body parity, all-original-matrix-method acceptance, whole client compilation and private-original publication rights. This selected-bundle gate does NOT prove the 13 separately reconstructed R150–R152 methods in the same class.

Hosted Ubuntu and Windows CI independently compile a synthetic rs.Packet-linked matrix original plus three original auxiliary type classes. Separately supply **different** Java-only helper implementations, compile the matrix from source alone, and compare three selected method bodies (constructor, loader, downstream matrix helper) to the original JVM. Changed matrix method operations, missing Packet Java, missing loader selection or wrong SHA must fail. R160 regression is also rerun. No original SpawnPK assets or source are hosted.

## Scope and remaining blockers

Combining independent recovery evidence across R150–R161, **all 24 of the original 24 matrix JVM methods now have Java implementations with 3,780 original JVM instructions matched** (R159 20 methods / 1,432; R160 two / 2,287; R161 two / 61). This is NOT proof that all 24 have been assembled, independently compiled and verified within one full source class. Eleven methods have been recompiled together, while the other thirteen were independently reconstructed earlier. Nor does it prove original StackMapTable representation, classfile attributes or runtime compatibility.

**Next crucial integration:** assemble *all 24* verified private original matrix source method bodies into ONE original owner source, compile it against source-only dependencies, compare every original JVM member's Code and class ABI, then replace the missing game-linked binary with that complete original-source owner in the 1,271-Java whole-client compiler frontier. Original Packet alias/method member mappings and the provisional 9,335 non-rs class dependency ownership remain separate. Last measured full-client javac frontier stays **516 errors** until a new actual private full-source replay; no improved error count is claimed.
