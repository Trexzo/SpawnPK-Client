# R85 — original v309 364-op private settings-save method-body candidate

R82 recovered 42 regular original buffered-writer source patterns. R83 recovers five exceptional array/List/enum writes. R84 recovers the bounded File/BufferedWriter opening and Paths/Files/catch closing envelope. R85 accounts for the remaining original two JVM instructions: a standalone BufferedWriter.newLine immediately after the indexed array loop.

The exact original save method partition is:

- 20 JVM instructions: original File and BufferedWriter open prefix
- 253 instructions: 42 regular writer source regions
- 61 instructions: five exceptional writer source regions
- 2 instructions: standalone indexed-array newline after loop
- 28 instructions: writer close, Files copy/delete and Exception catch tail
- Total: 364 instructions, one typed Exception handler, 47 write(String) calls and 48 newLine calls

A private new-source candidate generator validates complete ordinal partitioning without overlap, unexplained gaps, missing writes or changed standalone newline. It then emits original-order private Java method-body text using only separately grounded R82/R83/R84 fragments. Inputs and outputs remain private with SHA256-pinned original JAR and aggregate-only public evidence.

Local usage:
python -m spk_recovery.private_save_method_candidate ORIGINAL_JAR PRIVATE_OWNER.class PRIVATE_METHOD "()V" NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_WHOLE_JAR_SHA256

The candidate has NOT been compiled as an original whole owner source, has not passed a 364-op typed CFG/operand parity verifier, and has not demonstrated original file-system side effects or game runtime equivalence. Real private original-JAR replay of the new R85 CLI is a separate pending gate.
## Exact original-v309 private binary measurement

Independent read-only direct JVM inspection of the pinned original settings-save method verifies the complete 364-opcode partition: 20 opening instructions + 246 across 41 six-op direct writers + seven across one enum writer + 23 for the indexed int-array loop + 27 for three guarded List filters + 11 for a two-enum write + two standalone newline instructions at original offsets 380/381 + 28 ending file/catch instructions. This totals 364 and accounts for 47 BufferedWriter.write plus 48 newLine calls. The public-safe aggregate is `research/v309-source-recovery/original-save-364-partition-r85.json`. This is **not** a report of the new R85 generic generator replaying against the original JAR, nor of source recompilation or runtime equivalence.

## Independent local Java 9 method compilation witness

A separate private Java method-body source was assembled directly from the SHA-256-pinned original v309 classfile's settings-save method and Java 9 StringConcatFactory bootstrap recipes. It was compiled with `javac --release 9 -g:none -proc:none` inside a distinct **compile-only owner and synthetic helper/enum scaffold**; the original JAR was not modified. `javap -v -c -p` compared the new method against the original. The candidate reproduces **all 364 instruction opcodes in ordinal order**, all **364 original instruction byte offsets**, all **nine explicit branch targets in instruction ordinals**, the single exact `Exception` catch region **(0..920 -> 923)**, classfile major **53**, private-static access flags, stack/locals **6/3**, bytecode size **929**, **46** original StringConcatFactory site recipe strings, original String `ldc` values and checked invocation descriptors, with **zero observed differences in these categories**.

**Important limits:** This is a verified, independently hand-assembled **method-level Java9 compilation witness**, not a run of the generic R85 CLI, not proof that its generated Java output compiles, and not an exact original-class/field/callee-identity proof. The candidate uses replacement owner/external classes and nested enums, so exact reference operands, original class metadata, helper implementation, field initialization and filesystem/runtime behavior remain **uncertified**. Original private Java source, literal property names, bytecode, scaffold binaries and the original JAR stay outside GitHub. Aggregate evidence: `research/v309-source-recovery/original-save-method-java9-compiled-witness-r85.json`.

## Stronger independent Java 9 same-owner operand witness

I reran the private Java 9 source reconstruction with the **original JVM owner internal name** and the same referenced static-field owner/type names. Synthetic **external class and nested-enum implementations** were compiled solely to satisfy missing dependency source. The original SHA-pinned JAR stayed unchanged. Independent `javac --release 9 -g:none -proc:none` plus `javap -v -c -p` comparison yielded **364/364 identical opcode positions and byte offsets, all nine explicit branch targets equal, one exact typed Exception handler, 929 method Code bytes, 53 classfile major version, identical 6/3 stack/local limits, zero differences across 179 non-dynamic member/class/literal reference site renderings, and zero differences across all 46 checked invokedynamic concat recipes and signatures**. This is stronger than the relocated-owner compilation witness recorded previously.

**Not an exact classfile or runtime certificate:** StackMapTable frame encoding differs (both have 10 frames); the owner class initializer and full 126-field metadata have not been replaced with original source in this compilation probe, and the synthetic external classes/enums do not preserve original implementations. This was independently assembled Java, **not** a run of R85's source generator or R66/R81 private original-versus-candidate verifier. No original Java source, binary, setting keys or obfuscated member names are in the repo. See `research/v309-source-recovery/original-save-java9-same-owner-operand-witness-r85.json`.
