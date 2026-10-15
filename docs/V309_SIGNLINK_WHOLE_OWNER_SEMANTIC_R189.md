# R189 — one original-named Java source reproduces all v309 Signlink method semantics

Client-only original-v309 source milestone #1004. Draft stacked on R188 #1081, original method staged proofs R183–R188.

## Major recovery milestone — exact original JVM semantic Code, not identical encoded bytes

The pinned private Java9 `rs/v/a.java` (R188 source ZIP SHA256 **a7172b3aae3a794bbd5a59f6de085a7ee7b68749a117671d5cf6b47a0fcd5288**) compiles independently with `javac --release 9 -g:none -proc:none -implicit:none`, an empty external/original compiled binary/source classpath, and exactly seven **NOT-ORIGINAL** compiler-only Java declaration helpers (ZIP SHA256 **23d81085f2a692f5d6fc60791c489bb9982b104d569d4037d6d8aa4e75a13f3d**).

An independent local complete-class `javap -p -verbose` analysis against exact original v309 rs/v/a.class SHA256 **d0dc35deddc8016c3fdcaf2615810efa200c042120b83bed86cad5d04b1c0ddc**, from original JAR SHA256 **ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38**, found:

| Same original class, one source-only Java9 rebuild | Verified local finding |
| --- | ---: |
| Original JVM method identities | 24/24 |
| Original decoded JVM instructions | **870/870** |
| Only non-identical JVM opcode encodings | **35 ldc → ldc_w** |
| Other opcode, referenced constant, operand changes | 0 |
| Branch destinations after conversion to instruction indices | All matching |
| Exception handlers (start/end/handler indices and catch type) | All matching |
| Method access flags, stack limits and local-variable limits | All matching |
| Full original field signature/access inventory | Matching |
| Whole classfile bytes and exact JVM instruction byte offsets | **NOT identical** |
| StackMapTable representation and non-Code attributes | Not completely equivalent |
| Original supporting runtime helper Java | **NOT recovered** |
| Fully compilable v309 original client / tested original runtime | **NOT achieved** |

The original class constant pool is **type-grouped** (integer constants followed by float, strings, class entries, etc.), while ordinary `javac` produces an incremental constant pool in usage/declaration order. In the recovered original-named Java source, 35 references originally encoded as one-byte-index `ldc` become two-byte-index `ldc_w`. The referenced JVM constant value, constant kind/tag, and floating-point raw bits (where applicable) remain identical. An opcode-level claim of 870/870 **byte-for-byte** original instructions would be false; the verified result is fully resolved **semantic JVM Code parity with an explicit, narrowly scoped encoding normalization**.

R187 originally **undercounted** the g() and <clinit> instruction bodies, despite matching their instructions: original g() is **115** instructions, <clinit> **38**. Correct totals: R183–R186 first 21 original methods = 469; R187 g()+initializer = 153; R187 first 23 = **622**; R188 run() = **248**; whole owner = **870**. The R187/R188 verifier constants, documentation and milestone comment were corrected.

## R189 fail-closed verification design

The new public Python verifier:
1. Replays all SHA-pinned R183→R188 private source/bytecode acceptance, then separately recompiles the exact R188 Java source with seven strictly allowed helper declarations.
2. Verifies original JVM class owner, superclass, Java 9 major/minor, interfaces, flags, full declared field ABI, generic field signature/constant-value identities, and **all 24** method names, descriptors, access flags, max-stack/locals, signatures and complete decoded instruction inventories.
3. Uses the existing `_normalized_instructions` strict decoder, CP-identity resolver and invokedynamic bootstrap argument resolution to reject missing/unresolved operands. **Only** opcode `0x12` / `ldc` may normalize to `0x13` / `ldc_w`, with the same constant-pool tag, literal content or raw IEEE bits.
4. Converts branch destinations, switch destinations and exception-handler ranges to stable **instruction ordinals** so a legitimate encoding width difference does not invalidate otherwise identical flow.
5. Requires the original 870 decoded instructions and **exactly 35** legitimate `ldc → ldc_w` widenings. All other opcode substitutions, operand changes, semantic control-flow changes, exception handler drift, field or method ABI changes cause rejection.
6. Reports StackMapTable encoding differences separately; does **not** assert JVM verifier acceptance, annotations, optional method Exceptions attributes, original execution safety, client/server protocol equivalence or redistribution rights.

Dedicated hosted tests compile **invented, unrelated** Java9 classes in two different source declaration orders. The fixtures deliberately force `ldc` to widen across a constant-pool threshold inside a method with branches and an exception handler. Negative fixtures modify strings, branches, caught exception type, field access modifiers or method count. No original JAR/Java source is published to CI.

## Recovery scope still remaining

The `rs/v/a$a` original nested owner is a three-constant Java enum whose JVM fields were obfuscated. R188/R189 currently rely on a compiler-only *non-original* placeholder type, not original source. Six other supporting helper owners likewise remain original-unverified in this compilation. Complete Java-language reconstructed source for these must be independently proved before replacing compiler-only helpers.

Additional gates still required: exact private-input official R189 verifier replay, Java class verification/StackMap semantic acceptance without running production client behavior, full non-Code attribute review, full original client 1,279+ source integration and error-frontier measurement, original runtime/network/audio compatibility, source redistribution rights. No original source is committed to public GitHub and the **entire v309 client still does not compile**.

**Status: semantic whole-owner original method-Code recovery candidate; NOT complete original application recovery or byte-identical class. Keep DRAFT.**
