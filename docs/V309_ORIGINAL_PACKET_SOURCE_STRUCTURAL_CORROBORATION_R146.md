# R146 — Original-v309 Packet Java ↔ JVM owner structural correspondence

**Scope:** client-only exact-original source recovery, not a new server or emulator. Stacked on [R145 #1032](https://github.com/Trexzo/SpawnPK-Client/pull/1032), toward [source milestone #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

## Material original-v309 evidence

A **real private, read-only** analysis on the independently SHA-pinned original v309 JAR and all-source candidate ZIP found the candidate `rs/io/Packet.java` and original JVM class `rs/x/e.class` have **exactly the same multiset of all 91 declared non-static-initializer member access-and-erased-JVM-descriptor shapes**:

| Member kind | Original `rs/x/e` | Candidate `rs.io.Packet` | Matched shapes |
| --- | ---: | ---: | ---: |
| Fields | 11 | 11 | **11** |
| Constructors and ordinary methods | 80 | 80 | **80** |
| **Total** | **91** | **91** | **91** |

This fingerprint retains Java public/private/protected/static/final/synchronized/native/abstract flags, primitive types, array ranks, method parameter order and arity, constructor return void and method return type. It **erases binary names of reference classes**, because the deobfuscated Java source does not retain original obfuscated references. It excludes the original synthetic JVM class initializer `<clinit>` (which is represented through Java source initializers), so this is **not strict full classfile equivalence**.

Further independently verified anchors: the candidate explicitly initializes both `java.math.BigInteger` RSA decimal constants with **exactly the same 309-digit modulus and exponent 65537** as original `rs/x/e.class` JVM literal constant-pool entries. This is exact literal equality, not an assumed crypto signature. The original game-linked matrix class `com/a/b/a/b.class` directly references original `rs/x/e`, confirming why R145 needs this mapping to compile a source-restored matrix owner. This combination is substantially stronger than an obfuscated name guess.

### Implemented GitHub gate

New `PrivatePacketStructuralSourceR146.java` is a trusted **JavacTask.parse() only** AST census. It emits original candidate Java field and method access/erased-type shapes and BigInteger literal strings strictly to a private process pipe. No source execution, annotation processing or method compilation. `private_v309_packet_original_source_shape_r146.py` verifies exact whole original JAR and source archive SHA pins, parses the original `.class` members with the existing original classfile parser, checks the original matrix constant-pool class dependency, compares the two complete member-shape multisets **including multiplicity**, checks the exact two RSA literals, and emits just a sanitized source/JAR digest and boolean/count report (no user source, RSA decimal strings, original member names, classfile bytes, stderr or identifier-bearing maps published). Every original file is rehashed after analysis.

Run **only privately**:

```text
python -m spk_recovery.private_v309_packet_original_source_shape_r146 PRIVATE_ORIGINAL_V309.jar PRIVATE_PRELIMINARY_JAVA_SOURCE.zip FRESH_PRIVATE_REPORT.json --source-sha256 2f9903b5eb9c89eb736f806e0cbd0aa468e4cd2408eb436ec3fd03d3094e4536
```

Original JAR SHA-256 defaults to `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Fixed original owners `rs/x/e` and `com/a/b/a/b`; source relative path `rs/io/Packet.java`. Explicit overrides exist only for synthetic test fixtures.

Focused Ubuntu/Windows regression tests independently compile synthetic original JVM Java classes, a separate source-side class with different binary and member names but precisely matching shapes and RSA decimals, plus a matrix-like original dependent class. They test correct 4+4 structural correspondence, changed method arity, changed RSA digit, absent original owner dependency, changed source SHA and wrong top-level class. **No actual proprietary Java, assets or original classfiles enter public GitHub CI.**

## Hard acceptance boundary

A provisional `provisional_source_identity_structurally_corroborated=true` demonstrates **strong source↔original class identification** only. It is not original **method** correspondence: equal method/field-shape multisets do not reveal which source method corresponds to which original method, or prove instruction sequences, class constructor bodies, StackMapTables, extra attributes, inherited relationships, caller compatibility or actual runtime behavior. **Do not mark the source name mapping accepted, recompile the original matrix using guessed `Packet` method names, or reuse this as a bytecode-parity certificate.**

Next: derive one-to-one method/field mappings and verify original bytecode/IR witnesses (existing R25/R31/R32/R35/R36 etc.), then recover the original game-linked matrix class as independently compilable Java through R145 without an original binary fallback. The original `rs/x/e.class` changed bytes across v308 and v309 although the matrix class is byte-identical across those versions; class-name corroboration here is **version-specific**. The independently observed full client v309 Java compiler frontier is **516 remaining errors**, and R146 does not change that count.

Final goal remains the fully recovered and compiled `recovered-source/v309/src/` tree with independently owned third-party dependencies and provenance/rights checks.
