# R165 — restore complete original-v309 angle/math utility Java source

Client-only v309 recovery, stacked on R164 #1055, source milestone #1004.

The original class com/a/b/a/d.class (SHA256 **6b60fd4224532042707da6eda83c17879d0c5fcb0aaa478b9fcc035ed6bdda6b**) was previously represented solely by an unverified compiler signature scaffold. Its complete actual original-named Java source has now been reconstructed privately from original v309 JVM evidence.

## Independent real v309 Java9 rebuild

The original class is 891 bytes, with **6 methods, 10 fields and 81 decoded JVM instructions**. The source-only Java9 rebuild, compiled with an **empty original project/external classpath**, matches **81/81 instructions**: constructor throwing Error, integer-angle to float conversion, atan2+Math.round angle conversion, two array-based sine/cosine lookups and static 16384-element trigonometry lookup-array initializer. It preserves original operand evaluation and branch structure, not merely mathematically equivalent outputs.

In addition to matching all 6 JVM Code bodies and field ABI, the original and rebuilt class show identical **javap -p -constants** field/method declarations, including original eight static-final numerical ConstantValue literals (and the remaining static-final array fields). These constants need separate checks: method bytecode equality alone does not prove an unused constant's value. Original/rebuilt are both 891 bytes, but differ in SHA: rebuilt **7d4df6ec65f4b087a3c74e5e21e77407e7e32e3f2311aa44cfd221c27029ea0e**. No full classfile-byte parity or runtime claim is implied.

Private exact source inputs and outputs:
- Original v309 full JAR SHA: ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38.
- Original angle Java file SHA: bf41154240be19b1f1be5353c44db1e858406ae8f94779de66d32d9e7887013a.
- Private one-class angle Java ZIP SHA: 8f2ecf6d07cf7983f1c92ba73b4b83cda0d197f22a2a8b51477be96ddb6629a6.
- Previous private 1,273-Java recovered-source ZIP SHA: 758ea72c391a02bd0fc4762d26e0fdef32af44bea0b342589f1139c77874516a.
- NEW PRIVATE 1,274-Java source-tree ZIP SHA: **e9f641417e95de3c25c6534dff199e8d2d8a47f92d5250c40a0158a32ca588f6**.

Exactly one real original-derived Java owner is added into private recovered-source/v309/src/, preserving all 1,273 previous Java source files byte-for-byte. No guessed Packet or other math-type scaffolds are added to canonical source.

## Actual private whole-client compiler delta

All three tested candidates use javac --release 9 -proc:none -implicit:none, JDK only, empty original/external classpath, all Java files explicitly compiled, max 10000 errors:
- Baseline 1,271 Java: **2391 errors**
- + recovered matrix at 1,272 Java: **2364 errors**
- + recovered vector at 1,273 Java: **2358 errors**
- + recovered angle utility at 1,274 Java: **2355 errors**

Thus adding proven Java for the original matrix + vector + angle utility reduces the same JDK-only compilation diagnostics by a net **36 errors**. This measurement is not directly comparable to historical 516 errors on the provisional original-derived diagnostic dependency capsule. The whole client **still fails compilation** and no new error reduction is asserted for the normalized dependency frontier.

## New GitHub acceptance and CI

R165 reuses R164's strict full original Java class JVM Code/field/method/StackMap-separate source verifier, then adds a fresh **javap constant declaration equality** guard for all original static-final ConstantValue fields. It must pass BEFORE copying one exact verified Java source owner into the private 1,273-file source tree. The public GitHub tests are synthetic generic original-JVM angle helpers and separately compiled source, including a negative test that changes a PUBLIC UNUSED constant: method instructions still match but ConstantValue declarations differ, so the verifier must reject.

Ubuntu/Windows CI rerun both R165 tests and R164 full original vector source tests. No private original Java, game JAR or SHA-pinned source archive is committed to GitHub or hosted CI; only verification software, synthetic test fixtures and sanitized evidence.

The original auxiliary classes com/a/b/a/a and com/a/b/a/c, original Packet rs/x/e and the remaining client source dependencies still lack accepted complete original implementations. All recovered source and original bytes remain private pending ownership/redistribution rights. A successful one-class source rebuild or reduced JDK-only diagnostic does NOT establish whole-client compilation, original external binary provenance or runtime compatibility.
