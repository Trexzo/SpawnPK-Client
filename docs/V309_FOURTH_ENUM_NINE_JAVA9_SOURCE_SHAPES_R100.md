# R100 — exact Java9 source-opcode shapes for all nine original fourth-enum methods

The pinned original v309 (`client(7).jar`, SHA-256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`) has a fourth owner-nested enum with a source-invalid collision: its inner simple name is the same as its outer owner's. Independent `javap` inspection finds exactly **five fields, nine method bodies, two enum constants and two compiler-generated synthetic accessors**. The original's nine JVM opcode sequences comprise: values (4), valueOf (5), four-argument JVM constructor (11), two ordinary private-String getters (3+3), generated enum-values helper (11), two private-String synthetic outer accessors (3+3), and class initializer (19).

A separate `javac --release 9 -g:none -proc:none` compilation of a surrogate Java nested enum with exactly two constant constructors, two private String fields, two public getters and two outer-class accesses reproduced **all nine opcode sequences in their original ordering**, not just the accessors. This evidence does **not** establish constant strings, member names, field aliases, invoked operand references, bytecode metadata, source authorship or client runtime equivalence.

## Code

`spk_recovery.private_fourth_enum_nine_shape_witness` compares original and independently compiled candidate class profiles with SHA-pinned private JAR inputs. It requires the strict R99 inventory first (Java9 enum, 5 fields, 9 methods, 2 private Strings and 2 exact synthetic accessors), a common outer owner and distinct nested candidate class IDs. The gate classifies all nine methods by original signatures, opcode patterns, and which exact private fields are read; no obfuscated accessor or getter name is guessed, published or silently aliased. The accepted report explicitly retains false flags for R95 parity, original literals/operands, `InnerClasses`, and runtime equivalence. Positive source-to-classfile Java9 regression and negative opcode, missing accessor and owner tests are included.

CLI: `python -m spk_recovery.private_fourth_enum_nine_shape_witness ORIGINAL_JAR SURROGATE_JAR ORIGINAL_ENUM.class SURROGATE_ENUM.class PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --candidate-sha256 CANDIDATE_SHA`

## Acceptance boundary

This is **source-shape recovery only**. The strict R98 transformation and R95 all-four enum + ordered `InnerClasses` acceptance remain required. Source alias-to-original semantic name equivalence, actual original-private CLI replay, owner R97 composite Java9 verification, external helper behavior and gameplay/runtime certification are outstanding. No original class identities, obfuscated member names, literal keys, JARs or recovered proprietary Java are committed to GitHub.
