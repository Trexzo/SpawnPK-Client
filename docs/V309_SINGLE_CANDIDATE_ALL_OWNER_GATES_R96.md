# R96 — one exact-v309 Java 9 candidate, three independent acceptance gates

R93 assembles all ten original settings-owner method source forms; R90 compiles a private owner from source and checks the 697/364-op methods, the 93 static initializer writes and all 126 fields. R94 checks all nine ordinary methods. R95 checks four original nested enums **and** the ordered symbolic `InnerClasses` metadata that the flattened fourth-enum workaround cannot reproduce.

R96 composes these existing checkers. It invokes R90 **exactly once** to obtain one private compiled candidate JAR, SHA-pins that JAR, then runs R94 and R95 against the same original/candidate byte streams. An incomplete original ten-method declaration set, absent nested class, altered initializer, missing field, mismatched static/callback operand or changed `InnerClasses` metadata vetoes acceptance. Intermediate output is built in a private temporary directory and removed on error. Only after all gates pass does R96 atomically publish a locally private candidate JAR and aggregate JSON. The original and candidate JAR SHA256 values and original class identity must be verified before or during every gate.

Synthetic/mock-backed integration tests cover successful all-three-gate ordering, same candidate and SHA, absent original method, changed candidate pin, rejected R94 lambda method and rejected R95 fourth enum metadata. The existing R90/R94/R95 Java9 and classfile tests remain the semantic verifier tests; the R96 tests check all-or-nothing orchestration. No original JAR, private candidate, source, keys or obfuscated names may be committed.

Usage from a private checkout with complete v309 original JAR and R93 owner source tree:

`python -m spk_recovery.private_complete_v309_owner_acceptance ORIGINAL_JAR ORIGINAL_OWNER.class ORIGINAL_LOADER ORIGINAL_SAVER PRIVATE_JAVA_SOURCE_ROOT ORIGINAL_OWNER.class CANDIDATE_LOADER CANDIDATE_SAVER LOAD_ALIASES.json SAVE_ALIASES.json CLINIT_ALIASES.json NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA256 --javac JAVAC9`

This command has **not** passed original-v309 replay or whole-source compilation. A fourth nested enum with the known Java source-name collision currently fails R95's exact metadata gate. Passing R96 would show only bounded classfile/declaration/operand parity of this owner and its four nested enums; it would **not** certify external helper implementations, original callback side effects, configuration filesystem behavior, authorial source identity, gameplay, or runtime equivalence.
