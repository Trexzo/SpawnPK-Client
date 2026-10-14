# R156 — compile selected original matrix Java methods with source-only private helpers

CLIENT-only original v309 source recovery, stacked on R155 #1046 and milestone #1004.

The matrix source recovery has 16 original method implementations and 631 original JVM instruction matches, but the remaining six non-Packet methods reference original related math owners. Original v309 contains com/a/b/a/a.class (12 float component fields) and com/a/b/a/e.class (3 float fields and vector constructor/operation). We MUST NOT use their original class binaries as compiler dependencies or claim they are independent third-party libraries.

R156 extends the R150/R155 SHA-pinned source-only Java method verifier with an OPTIONAL separately SHA-pinned PRIVATE scaffold source ZIP. It must hold 1–3 Java files under exact original-v309 non-rs JVM class owner paths, each original classfile proven to exist in the full SHA-verified original client JAR. The helper owner may NOT be rs/, the recovered matrix owner, a duplicate or a casefold alias. No additional original binary is ever added to compilation.

Compile the original matrix owner Java source and the original-named Java helper scaffold SOURCE together with javac --release 9, annotation processing disabled, EMPTY original/external classpath and EMPTY sourcepath. Reject unexpected generated .class owners. Verify only the explicitly selected reconstructed MATRIX methods against ORIGINAL JVM Code: full opcode/offset/branch/constant/reference sequence, access and stack limits, handlers; StackMap metadata compared separately. Compiled helper methods remain UNVERIFIED; their presence supplies only type/field signatures to the compiler.

Reports include helper source SHA and count, with unconditional false acceptance flags for helper-original-source parity, original binary fallback, whole matrix behavior, full client compilability and source redistribution. All original client inputs and private recovered/scaffold source remain off public GitHub. The SHA pin is reverified at the end.

Cross-platform synthetic CI: compile a genuine original game-linked ext.Matrix against rs.Game and ext.Helper classfiles; compile an independent Java Matrix source together with a minimal ext.Helper Java source, NOT the original helper class binary; prove exact selected matrix Code. Fail if the helper Java is absent, its field type is wrong, its original class owner is invented, it tries to inject rs.Game, or its SHA is wrong. R150 and R155 suites rerun.

This enables the next source restoration of original matrix/vector-component methods while preserving the boundary: compilation-only scaffold is NOT original source recovery. The independent full v309 client original-source javac frontier remains at 516 errors.
