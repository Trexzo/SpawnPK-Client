# R159 — recover exact original v309 matrix determinant float source with bounded bytecode stack lifting

Original SpawnPK v309 CLIENT only. Stacked on R158 #1049 and source milestone #1004. Original user-derived Java/source, compiled derivatives and classfiles stay private.

## Actual original private Java method reconstruction

Original v309 matrix JVM owner com/a/b/a/b.class SHA-256 52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030, full original JAR SHA-256 ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38.

The original package-private g():float determinant routine consists of 480 straight-line JVM instructions ending at bytecode offset 731. It reads 96 original float-array positions and combines float products and sums/differences with a precise original operator association. An independently developed private stack-machine expression lifter reconstructed the matching Java return expression, retaining every nested float operation without algebraic reassociation. The original routine has NO branches, method invocations, writes, loop state, exceptions or indirect method dependencies.

Private Java9 javac --release 9 with NO original project JAR/other binaries on the classpath yielded exactly **480/480 original JVM instructions**, matching all original offsets, ordered field/array accesses and float operations. This is independent method instruction-level evidence, not full classfile, StackMap, source ownership, runtime or whole-project rebuild acceptance.

Combining this determinant body with the six privately recovered original matrix Java methods from R158, all SEVEN selected methods were compiled in ONE private Java owner alongside the same three unverified source-only helper Java classes. All **1082/1082** selected JVM instructions match original:
- Euler helper c():float[] 108
- Euler helper d():float[] 113
- 4x4 toString():String 60
- original transform component writer 93
- axis vector output 68
- quaternion rotation input writer 160
- determinant g():float **480**

The earlier original matrix total was 19 selected methods / 952 original instructions. This adds exactly one independently rebuilt method, reaching **20 of 24 original matrix methods and 1432 original instructions**. The remaining FOUR originals are two Packet-dependent constructor/loader routines and two longer matrix multiplication/inversion/transform operations.

Exact private source input snapshots after this reconstruction:
- private seven-method original-name Java owner ZIP SHA-256 dd804e1bf7373554de0234b03e8d0a202b305635e77f5aa1f4c5c71f63b742ac
- private three Java-source helper ZIP SHA-256 fc1939737d32ad1cae46011e0166ccf71c029bccf6431653eef1f6ff3ab2427b
- private seven-method selection JSON SHA-256 47b8c7af6d090fb9abfe702052647d89c795ca775078394cd194253b934083b2

## Reusable GitHub source recovery solver

R159 adds a guarded SHA-pinned original JVM to Java float-stack-expression lifter. It does NOT contain original game Java or JVM class bytes. It verifies an exact original classfile owner, a unique float() method and one instance float[] field, then calls the trusted installed javap with controlled environment on the pinned original JAR. It accepts ONLY a tightly limited JVM vocabulary: this-reference, the proven instance float-array field, small nonnegative array indices, faload and ordered fadd/fsub/fmul/fdiv finishing in freturn. It rejects branching, invocations, mutations, exceptions, other fields, stack manipulation, conversions, duplicate/changed code offsets and unbounded expressions.

Every accepted JVM float arithmetic operation becomes a parenthesized Java expression node preserving operand evaluation order; no simplification or guessing of original semantics. Generated source stays private and MUST be independently compiled back to original instructions; R159's generator output alone is not a method acceptance certificate.

Cross-platform Ubuntu and Windows synthetic tests independently compile a generic float-array method with chained floating-point operations, lift the JVM Code back into Java source, then recompile and compare normalized resolved instructions with original. Negative tests cover unexpected branching, original SHA mismatch, exact instruction-count drift and wrong class field. R158 six-method regression runs too. Hosted CI never receives SpawnPK private originals.

Actual full client 1,271-Java original-source compiler frontier remains the previously observed 516 errors. The current one-class partial source is not integrated into that full build, so no decrease, full client compilability, external dependency ownership or source publication authorization is claimed.
