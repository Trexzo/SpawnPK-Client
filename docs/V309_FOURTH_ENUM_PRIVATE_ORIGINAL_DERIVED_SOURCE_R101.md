# R101 — recover a *private, Java 9-compilable* fourth-enum source candidate from exact original v309

## Independently replayed exact-original source witness

A separately performed private local experiment against complete original `client(7).jar` (SHA-256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`) found the unique owner with 126 fields, 10 methods and four nested enums. Its fourth nested enum has the source-invalid outer/inner name collision but otherwise uses Java9 compiler-recognizable enum construction: two constants, two private String data fields, two public getters, two synthetic outer-field accessors and all nine original methods.

A **private actual-original-derived Java source** was created using all six original initializer String literal values, the exact two private String field names and the original getter names/field relationships. `javac --release 9 -g:none -proc:none` compiled this source successfully. A fresh original-JAR versus source-compiled `javap -c -p` comparison found **9/9 exact opcode sequences** with lengths `[4,5,11,3,3,11,3,3,19]`; private source SHA-256 is `e977bdd5bb39b2b63a4a3df726ffa7fb45961f00a6fbf688b1990a66f98a6f7f`. Original Java source, literals and obfuscated class/member names remain **outside GitHub**.

## R101 reproducible private source emission

`spk_recovery.private_original_fourth_enum_source_emitter` reads a **SHA-pinned complete original v309 JAR** and an explicitly selected original outer owner class. It refuses missing or duplicate archive entries, missing fourth enum, invalid Java identifiers, unsupported initializer sequences, malformed or unsafe Java string literals, and source/field/getter ambiguity. It requires the strict R99/R100 original enum shape before emitting source.

It produces a **new private-only** `private-java-source/<package>/<outer>.java`, compiles with `javac --release 9 -g:none -proc:none` into `private-java9-source-candidate.jar`, and retains files only if all nine original/candidate opcode sequences match and the **six exact original initializer literals, two private String field identities and two getter-to-field relationships** also match. It records a non-secret aggregate with original/candidate SHA pins and every noncertification flag. Compiler diagnostics and private source are never printed in CI or put in GitHub.

The recovered source must use a legal temporary nested enum class simple name. This output is a **source capsule** with a stub outer owner; it is not an executable full game client. R98's collision rebinding, R99's synthetic member-name normalization and the original six-entry outer `InnerClasses` metadata remain separate validation work.

## Tests and limits

Hosted synthetic Java9 tests compile an exact structural mock original and exercise a private source/candidate roundtrip; they reject altered original complete-JAR SHA, unsafe literals, missing fourth enum, missing Java compiler and existing output directories. The actual private-original source reconstruction was tested independently with `javap`; a full private R101 CLI invocation against the actual original remains a separate needed gate.

**No R95 acceptance, R97 owner assembly, alias-free obfuscated field identity, original authorial source, external helper runtime behavior or whole-client runtime equivalence is asserted.**

Example private use:

`python -m spk_recovery.private_original_fourth_enum_source_emitter ORIGINAL_V309.jar ORIGINAL_OWNER.class NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --javac JAVAC9_OR_LATER`
