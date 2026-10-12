# R81 — exact original-v309 versus recompiled full-method JVM operand gate

R66 deliberately verifies only structural JVM parity: complete method opcode shape (allowing `ldc` versus `ldc_w`), branches, ordered typed catch table and exact declared static-write order. R81 adds the missing **semantic instruction operands** check on a separate compiled candidate.

For one original and one candidate JAR, each pinned by its complete SHA-256, R81 first requires the existing R66 check to pass. It then compares **every** JVM instruction at the corresponding ordinal, including exact constant-pool tags, original String/primitive literal values and raw floating-point bits; local-variable indices and increments; field reads and writes, helper method calls and descriptors; invokedynamic call signatures and semantic bootstrap method/arguments (not unstable constant-pool numeric indices); array/type operands; and labelled switch case targets. All owner field and method renaming requires private explicit injective aliases. Unexpected new bytecode-profile operand keys fail closed.

The private alias JSON schema accepts the existing R66 `aliases` array for original-owner static writes, plus `read_only_field_aliases` and `method_aliases` arrays with the same original/candidate name/descriptor format. Identity names in unchanged same-owner classes need no extra aliases. The compiled candidate must already have been built and have its own pinned SHA. R81 does **not** build or invent the missing Java candidate.

Private execution:

    python -m spk_recovery.whole_method_operand_parity ORIGINAL_JAR ORIGINAL_OWNER.class ORIGINAL_METHOD "()V" CANDIDATE_JAR CANDIDATE_OWNER.class CANDIDATE_METHOD "()V" PRIVATE_ALIASES.json NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --candidate-sha256 CANDIDATE_SHA

Research-only output consists of private aggregate counts, hashes and **explicitly false** side-effect and runtime parity flags. A pass does not prove original helper implementations, nested enum class behavior, other owner methods or full client compatibility.

The original private v309 method has **not** been recompiled as a complete equivalent candidate and this new R81 tool has **not** been replayed on an original-versus-recompiled full method. Synthetic Java 9 end-to-end profile mutation tests are included. Never publish original JAR, recovered private member identities, literal keys, candidate binary or source on GitHub.