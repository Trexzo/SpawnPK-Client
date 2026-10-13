# R113 — recovered original-v309 364-instruction saver Java9 source

## Independent actual-original private source proof

The exact complete original v309 `client(7).jar` SHA256 is `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. The original owner has 126 fields and ten method declarations. R111 recovered the source and validated seven ordinary methods; the remaining two are an original **364-JVM-instruction private static settings writer** and **697-JVM-instruction public static settings reader**.

**New actual-original local reconstruction:** generated a private Java source body for the complete settings writer, including original file creation, 47 `BufferedWriter.write` sites, the indexed key-binding loop, three conditional spellbook-filter writes, an optional enum-name pair, file copy/delete operations, all nine explicit control-flow branches, and the one typed Exception handler. The original JAR was read only with `javap`; **the original client was not executed**.

Recompiled this source in a separate partial 126-field/four-enum Java9 owner with `javac --release 9 -g:none -proc:none`, using clearly identified **nonoriginal external type stubs** only to satisfy compilation. An independent original-versus-new-source `javap -p -c/-v` comparator checked:

| Private original-method check | Finding |
|---|---|
| Original/source JVM opcode sequence | **364 / 364** exact |
| Resolved symbolic instruction operand differences | **0** (includes original `StringConcatFactory` recipes) |
| Original/source branch destination ordinals | **9 / 9** equal |
| Original/source ordered typed exception regions | **1 / 1** equal |
| Method max_stack/max_locals | **6 / 3** exact |
| JVM Code byte length | **929** in each |
| Original StackMapTable frames | **10** |
| Raw source javac StackMap encoding difference | **One** at frame #2: source `append_frame(308, [BufferedWriter,int])`, original `full_frame(308,[top,BufferedWriter,int],[])` |
| Separate bounded candidate verification metadata rewrite | +5 bytes, producing **10/10 exact original frame forms**, without copying original Code |

SHA256 of private recovered saver Java body: `0ec3a0899b7eaa60ba976baf033582e571a3055611749daa594299e01305e2ff`. Source-compiled partial owner: `c2b1d7ef6e3e32b2529efd75864512b98ae2a0f3494624a45ee5d8e20f78df54`. Source-compiled Java9 candidate JAR: `685899d2570555648751844c28d9808106be67f7dce2cf0516123913aa14fcd5`. Bounded metadata-only frame-corrected candidate: `e9a2841605ca9811dd1bc5fbcf155f32361b8627106e0fd1770febddd8462253`.

These comparisons are *independent actual-original evidence*, but the exact private R113 **R66/R81 tool** still needs its own local invocation. The helper and temporary enum classfiles do not prove original helper implementation or owner-wide runtime behavior.

## R113 strict reusable GitHub acceptance

`spk_recovery.private_recompiled_v309_saver_r113` accepts separately SHA256-pinned complete original/candidate private JARs and one exact owner class entry. It requires the original Java9 126-field/ten-method R112 owner inventory and exactly one original **private static `()V` 364-op method**, then checks the source candidate's exact method identity, 364 opcodes, code length 929, max stack6/locals3.

It invokes existing **R66 CFG/ordered typed exception handler check** and **R81 every semantic instruction operand, including invokedynamic bootstraps**, requiring exact 364 operands, nine branch edges, one Exception handler, zero original static field writes. Unlike R81 alone, R113 also requires the entire **original encoding** of all ten StackMapTable frames, including the specific `full_frame` not emitted by ordinary `javac9`.

The accepted private output is a **sanitized count/boolean/hash-only report**. No original source, original JAR, compiled candidate or private symbol names are uploaded. Tests cover bad pins, missing/wrong original 364-method identity, wrong StackMap frame, changed classfile version, R81 failure, removed exception region, existing output, and a separate **actual `javac --release 9` 364-instruction fixture that directly runs R66/R81**.

## Missing gates

Original **697-op loader source remains unrecovered**. This partial owner has only eight final assignments in its initializer and lacks the other 85 mutable-field writes and seven small owner methods in this particular R113 source artifact; R110/R111 separately prove their source forms. Merging all source pieces into **one candidate** and running R110→R106→R105→R104→R95→R94/R58/R88/R107 remain outstanding. The original client and any original save-file side effects were **never executed**.

Private CLI:

`python -m spk_recovery.private_recompiled_v309_saver_r113 ORIGINAL.jar RECOMPILED_FRAME_CORRECTED_CANDIDATE.jar ORIGINAL_OWNER.class FRESH_PRIVATE_REPORT --original-sha256 ORIGINAL_SHA --candidate-sha256 PRIVATE_CANDIDATE_SHA`.
