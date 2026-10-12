# R102 — all nine exact original-v309 fourth-enum JVM operands, under bounded generated-member aliases

## Actual original-v309 private evidence

The original SHA-pinned complete v309 client JAR (`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`) uniquely identifies the original settings owner (126 fields, ten methods), its four nested enums, and the fourth enum's source-illegal outer/inner simple-name collision. A private original-derived Java9 source capsule now compiles successfully using six exact original initializer literals, the two exact private String field identifiers, the two getter names/field relationships, and the original **synthetic accessor field-read order**.

An independent original-JAR vs `javac --release 9 -g:none -proc:none` reconstructed-candidate `javap -c -p` instruction check found **9/9 exact original opcode sequences** and **zero resolved operand differences** after only **three generated enum field aliases** (two enum constant JVM IDs + values backing array), **one generated values-helper method alias**, and the temporary nested type name; the two synthetic accessor bodies read the same actual private fields in the original method order. Real private source SHA-256 `91d96e06c645b5403439556d6ebb7f4e3522e9c83161d22ef568f9e2fe2fe081`. No actual source, JAR or private member/literal data is published here.

## Strict structural + semantic operand verifier

`spk_recovery.private_fourth_enum_exact_operand_parity_r102` provides a **separate, SHA-pinned, exact resolved JVM instruction operand comparison**. It requires the strict R99/R100 nine-method original and candidate enum inventory, original colliding binary identity, matching original outer owner, exact Java9 class headers and all five field descriptors/access/metadata. A field-name alias is allowed **only** for the two generated enum constants and one values backing array; ordinary private String fields must preserve their exact JVM names. Getter names must match exactly. The generated values helper and two synthetic accessor names are mapped strictly by method signatures and which exact private String field they read. The candidate nested binary class name is normalized to the original collision type solely for this bounded comparison.

For all nine method declarations and every decoded JVM instruction, the gate compares opcode, symbolic resolved operands, class/value references, constants, max-stack, max-locals, handler and StackMap metadata. It rejects any literal mutation, ordinary data-field alias, foreign invocation change, shape drift, incomplete field inventory, missing method or changed original SHA pin. Output is an aggregate-only private report; no identifier or literal values are exposed.

Synthetic hosted tests build two **real Java9** enum variants from ordinary source. Positive test requires all **62 resolved instruction rows** across nine methods; negative tests cover changed original string constant, private field drift, malformed accessor body, mismatched outer owner and wrong original JAR SHA.

## Remaining blockers

This is a **source-derived method/body and operand parity proof**, not source authorship and **not R95 all-four enum classfile acceptance**. R95 still requires the candidate owner to reproduce the complete original **six-entry ordered InnerClasses table**, all four nested enum classfiles with the exact colliding binary names, and exact field/method alias restrictions. R97 also requires complete Java9 owner source and all its methods. Actual private R102 CLI replay against exact v309 JAR remains a separate mandatory acceptance step from hosted synthetic CI. Whole client runtime/gameplay equivalence remains unverified.

Private CLI:

`python -m spk_recovery.private_fourth_enum_exact_operand_parity_r102 ORIGINAL.jar SOURCE_CANDIDATE.jar ORIGINAL_OWNER.class ReconstructedEnum NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --candidate-sha256 CANDIDATE_SHA`
