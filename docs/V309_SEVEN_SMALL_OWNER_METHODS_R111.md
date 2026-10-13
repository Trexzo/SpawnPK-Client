# R111 — seven original owner methods after exact Java 9 compilation

## Pinned real original-v309 evidence, not a fixture claim

Read-only original complete `client(7).jar` SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Independently recovered a private Java9 source owner with the original 126 JVM field declarations, four nested source-legal enums, all **93 exact ordered initializer writes** (213 original decoded initializer instructions, two `ldc`→`ldc_w` compiler width changes), and **seven of nine original ordinary owner method opcode sequences**.

The seven exact original method lengths are **3, 2, 2, 2, 20, 4, 41 = 74 total instructions**. They represent one no-argument constructor, three Boolean methods, one Boolean state-transition method with original branch and external field target shapes, one callback-registration method, and one integer array-setup method with ten original entries. All seven match the real original method opcode sequences after independent `javac --release 9 -g:none -proc:none` compilation. The callback's JVM `invokedynamic` is a LambdaMetafactory reference to the original 364-op private static method, preserving the method-handle *symbol*; actual callback behavior is **not** recovered or executed.

Private original-derived Java source SHA256 `579bc18c8e3465c9a93a088b1940ffed473068ebf196e295ba182045a1a5baef`; Java9 candidate-with-stubs JAR SHA256 `471b1ea96c8dd10e66bec5b698ed87c0cacb217cfc74d7562454b765b3445750`.

## Important nonoriginal pieces in the candidate

The original **364-instruction** private method currently has a **one-instruction `return` placeholder** in the private candidate, ONLY to let the method reference compile. The original **697-instruction** public method is absent entirely. These are the two remaining original ordinary method bodies. The source compiler also emits two explicitly source-only outer String getter helper methods to trigger the fourth nested enum's synthetic private-field accessor generation; these extra owner methods are **not original**, must disappear when recovered source replaces them, and must NOT pass R88 or R94. Additional private external helpers for the callback, switch flags and string builder are nonoriginal interface/type stubs; not behavior parity.

## R111 reproducible private gate

`spk_recovery.private_seven_owner_methods_preflight_r111` checks independent complete SHA-pinned original and source-built candidate JARs. It requires the previous **R110 213-instruction / 93-write initializer preflight**, the full original **ten owner-method** inventory with exact original method sizes `2,2,2,3,4,20,41,213,364,697`, and exact candidate class member shapes for seven ordinary source-recompiled methods. Every one of those seven must match original JVM opcodes, declared method access and descriptors, stack/locals, exception tables, explicit branch target ordinals, field and method member-ref identities, integer immediates and literal types/values; the four-op callback also requires its fully resolved original LambdaMetafactory bootstrap target.

Fail closed unless the original 364-op method is present **only as a one-op placeholder**, the 697-op method is **absent**, and exactly two source-only outer String getter helpers exist with the proven temporary nested type descriptor and three opcode instructions each. This report explicitly marks R94/R58/R107 and original external runtime as **false**.

Hosted synthetic fixtures verify the seven method shapes and negative cases for changed opcode, callback bootstrap, field/helper target, missing method, unremoved extra source helper, wrong 364 stub and bypass of R110. They are not a replacement for actual-original R111 private CLI replay. Neither source nor original class identities/strings are committed.

CLI:
`python -m spk_recovery.private_seven_owner_methods_preflight_r111 ORIGINAL_V309.jar SOURCE_COMPILED_PARTIAL.jar OWNER.class Surrogate FRESH_PRIVATE_REPORT --original-sha256 ORIGINAL_SHA --candidate-sha256 CANDIDATE_SHA`

## Next gate

Recover the original **364 and 697 instruction method bodies** and remove the two generated source-only helper declarations and the 364-op placeholder, then run full R110→R106→R105→R104→R95 and final R94/R58/R88/R107 on a single independent source-recompiled postimage. The original client JAR was never executed and no whole-gameplay equivalence is certified.
