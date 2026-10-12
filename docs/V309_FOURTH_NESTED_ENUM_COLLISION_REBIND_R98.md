# R98 — fourth original-v309 nested enum: strict post-javac collision rebinding

## Independent exact-original observations

Private, read-only inspection of SHA-256-pinned `client(7).jar` (`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`) confirms one original top-level owner with 126 fields, 10 methods and exactly four nested enum classfiles. The original owner's ten method instruction counts are `[2,2,2,3,4,20,41,213,364,697]` (independent `javap` check). The fourth nested enum has a JVM inner simple name equal to the enclosing owner simple name, which Java source cannot declare verbatim. That fourth enum has original major 53, 5 fields, 2 enum constants, 9 methods and 1,165 classfile bytes. None of its private identifiers are published.

## Proposed bounded reconstruction route

Compile a structurally equivalent *temporary-name* Java nested enum under `javac --release 9 -g:none -proc:none`, then rebind the candidate's nested JVM internal name and `InnerClasses` simple name through a conservative constant-pool-only transform. The transform changes no method `Code` bytes and refuses ambiguous Java `String` literals, field/method identifiers, unrecognized descriptor/signature shapes, duplicate or missing archive entries, nonmatching SHA-256 pins and unverified original collision metadata.

R98's private CLI only promotes a rebinding result after **R95 accepts all four enums and both owner/nested symbolic InnerClasses metadata tables against the exact pinned original JAR**. The transform never copies classfile bytes from the original into the candidate and never alters the original. On rejection it publishes no compiled candidate. Source, obfuscated names, Java snippets, client binaries and callback settings keys remain outside GitHub.

Local synthetic Java 9 experiments have demonstrated that a rebuilt nested enum named identically to its outer owner can be loaded reflectively and used via `Enum.valueOf` with its methods still executable. R98 adds cross-platform synthetic regression tests, including original SHA mismatch, method-literal divergence, unsafe surrogate Java string literal and missing nested class vetoes.

## Crucial certification boundaries

**This is a bytecode reconstruction technique, not proof that javac can directly generate the original Java source declaration.** Synthetic demonstrations and passing hosted CI do not establish the real v309 fourth enum's method-body parity, identical original field IDs, external helper effects or overall client runtime equivalence. The original-v309 private R98 CLI remains to be run against a verified all-four-enum candidate; acceptance must be fail closed until that replay passes.

CLI:

`python -m spk_recovery.private_nested_enum_collision_rebind ORIGINAL_V309.jar PRIVATE_COMPILED_CANDIDATE.jar ORIGINAL_OWNER.class TEMPORARY_NESTED_SIMPLE_NAME NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --candidate-sha256 CANDIDATE_SHA`
