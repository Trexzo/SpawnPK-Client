# R99 — original-v309 fourth nested enum synthetic accessors

## Exact original binary evidence

Independent private inspection of pinned v309 `client(7).jar` (SHA-256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`) identifies the fourth owner-nested enum by **the original simple name equaling the enclosing owner's simple name**. It contains exactly five fields and nine methods, including two distinct private `String` fields and two `ACC_STATIC | ACC_SYNTHETIC` methods that each read one of those fields using exactly `aload_0; getfield; areturn`. Both synthetic accessors have one stack slot, one local and no handlers.

A separate Java 9 (`--release 9 -g:none -proc:none`) compile of a source-declared surrogate nested enum produced **the same two three-instruction accessor bodies** when the outer class referenced both private enum fields. That yields a concrete, compiler-explainable source pattern, *not yet an original-v309 candidate bytecode parity certification*.

## New strict private tool

`spk_recovery.private_original_fourth_enum_accessors` profiles the original and a surrogate candidate directly from separate SHA-pinned JARs. It enforces original nested-name collision and surrogate distinctness, the original Java9/enum header, exactly 5 fields, 9 methods, 2 unique private `String` instance fields, and one distinct exact 3-op synthetic accessor per field on **each** side. It requires identical names for the two actual private data fields rather than inventing aliases, and produces a private file mapping each original synthetic accessor to its unique compiler-generated candidate counterpart. Public aggregate output contains counts only, never obfuscated field/accessor names, JAR contents or recovered keys.

Importantly, the tool **does not rename methods or relax R95 parity**. This verified mapping is evidence for future binary reconstruction and must be integrated into an explicit, independently reviewed candidate transform before a full-original R95 pass is possible. The original owner's 6 ordered `InnerClasses` entries (four local enums, two foreign entries) remain an independent hard gate; merely rebinding a simple name or synthetic accessor does not reproduce that table.

## Regression gates

Real Java9 compiler tests validate exact synthetic accessor shapes and reject altered field reference, wrong return opcode, missing synthetic method, changed private data field and original SHA mismatch. No original client binary or recovered proprietary Java source is committed. Original full enum bytecode parity, `InnerClasses` order, R97 composite Java9 acceptance, external helper effects and original client runtime equivalence remain **uncertified**.

Private CLI: `python -m spk_recovery.private_original_fourth_enum_accessors ORIGINAL.jar SURROGATE.jar ORIGINAL_COLLIDING_ENUM.class SURROGATE_ENUM.class NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --candidate-sha256 CANDIDATE_SHA`.
