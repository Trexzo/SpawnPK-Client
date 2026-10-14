# R149 — original Java9 instruction-level parity for duplicate signed-short readers

**Client-only original v309** reconstruction, stacked on [R148 #1035](https://github.com/Trexzo/SpawnPK-Client/pull/1035), source milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

The original game-linked `com/a/b/a/b.class` matrix loader invokes original `rs/x/e.B:()I` **six times** during coordinate/transform decoding. Original method `B` increments one int cursor field by two, reads two bytes from one byte-array field in big-endian order, and converts unsigned 16-bit values greater than 32767 to signed values by subtracting 65536. **The original JVM Code attribute is 59 bytes long.** Preliminary decompiled `rs/io/Packet.java` contains **two byte-for-byte identical source reader bodies**, `method2616()` and `method673()`, with this same expression and identical field-access roles.

A real **private independent Java9 isolated recompilation** (2026-10-14) established that when *either* candidate body is compiled as a standalone method with its source int-cursor and byte-array fields bound to the *actual original B* field identities, javac emits the same **37 instructions** across **59 Code bytes**, offsets, branches, resolved member references and integer constant (including 65536 `ldc`) as original `B()`. **However:** original `B` has a StackMapTable **full_frame** at offset 57 with locals `[top, int]`, while isolated javac emits **append_frame** at offset 57 with locals `[int]`. These are not bytewise equal stack-map representations. Instruction/operand parity is supported, **full JVM Code-attribute parity is NOT**. No original game binary or original source JAR was put onto the javac classpath. It **does not tell us which source method name represents the original B**, because both are equal, and does not prove the complete original Packet owner or matrix loader compiles.

## GitHub R149 implementation

- SHA-pin the exact complete original-v309 JAR and 1,271-Java source ZIP. First require the existing R146/R147 whole-Packet-member + RSA source-owner identity corroboration, with no arbitrary individual-name acceptance.
- Read the exact original `B:()I` via the existing trusted JVM classfile Code/constant-pool parser; require unique original public instance `B`, exactly 59 Code bytes, no external invokes or exception handlers, and exactly two original field types used (one `I` and one `[B`). Determine the original cursor and payload field identities solely from the original B field bytecode, not human guesses.
- Use a trusted **`JavacTask.parse()` only** helper against the exact preliminary Java source. Find exactly two zero-argument public `int` methods whose canonical AST body matches the signed 16-bit logic and each other; capture the actual Java method span and every verified `this.caret`/`this.payload` member-select span. Reject extra candidate methods, unequal canonical method bodies, wrong access counts or source syntax/offset problems.
- Assemble each method independently as a minimal fresh Java class using the original binary *owner/field/member identities*, changing the source candidate only at AST-verified field spans and the exact method declaration identifier. Compile **twice independently** with `javac --release 9 -proc:none -implicit:none -g:none` and completely empty original/external classpath and sourcepath. No original client runtime is executed.
- Parse those newly compiled JVM classfiles and compare original B vs each: **full normalized decoded opcode/instruction operand stream**, original/member field references including resolved CP operands, branch destinations/offsets, constant raw bits, code length, max stack/locals, exception handlers, member access flags and resolved StackMapTable evidence. Only CP index addresses (classfile layout details) may differ in the instruction comparison; no bytecode operations are silently disregarded. **Different StackMapTable metadata is reported as a separate failed strict-parity property** and cannot be silently normalized into full JVM Code parity.
- Default output is a sanitized **private-only** JSON report with two passing body-witness counts, class/source SHA pins, checked properties, and explicit `original_to_source_member_identity_uniquely_determined=false` and `matrix_java_source_recovered=false`. Even full parity in this isolated body is not blanket parity for `rs/io/Packet.java`; independent field owner alias semantics and original matrix caller restoration remain required.

## Synthetic CI

On Ubuntu and Windows, compile independently a synthetic original Java9 owner with its real signed-short `B` plus a same-signature ambiguous sibling, cryptographic RSA constants and matrix-type dependency; construct a **different-source-owner candidate** with two identically implemented signed-short reader methods. The official R146/R147 source-owner structural gates must agree before isolated body parity. Tests deliberately alter one duplicate body, alter original B's implementation and change the whole-original SHA to ensure fail-closed behavior. No SpawnPK original classfiles, Java source, assets or private identifiers are uploaded to public GitHub Actions.

## Exact private replay

```text
python -m spk_recovery.private_v309_packet_signed_short_body_parity_r149 \
  PRIVATE_ORIGINAL_V309.jar PRIVATE_PRELIMINARY_SOURCE.zip FRESH_PRIVATE_R149_BODY_PARITY.json \
  --source-sha256 2f9903b5eb9c89eb736f806e0cbd0aa468e4cd2408eb436ec3fd03d3094e4536
```

Original expected SHA-256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Exact R149 CLI full private-source replay and external CI remain gates; the independent real isolated proof is reported separately rather than passed off as the repository CLI output. Original complete Java source-tree compiler error frontier remains at **516**, no new full-source compiler reduction claimed.

**Next:** verify the exact original matrix method dependencies and recover source for the matrix class, using this *equivalent body family* without arbitrarily assigning the original B to one of two decompiler method names. Full `recovered-source/v309/src/` is still incomplete; non-rs dependencies are not independently licensed or certified by this method-level witness.

## Exact original-v309 StackMapTable discrepancy

In the independent *actual private v309* verification, both source candidates match **37/37 decoded instructions and the same 59-byte Code sequence**, but the original B method encodes its verifier state as `full_frame(255)` at bytecode offset 57 whereas isolated Java9 javac uses `append_frame(252)` at the same offset. The report now distinguishes the instruction-level acceptance predicate from strict frame metadata. The JVM Code subattribute is **not byte-identical**; `whole_original_code_attribute_parity_accepted=false` is unconditional. No canonical original source method name or full class parity is claimed.
