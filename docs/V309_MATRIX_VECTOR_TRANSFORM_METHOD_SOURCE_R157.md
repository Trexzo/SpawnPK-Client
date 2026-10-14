# R157 — restore original matrix component import and vector scale Java methods

Original-v309 CLIENT source recovery. Stacked on R156 #1047 and R155 #1046; full source goal #1004.

## Private original method reconstruction

The exact original linked matrix class SHA is 52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030. Private Java9 source recovery of two further original methods now compiles with exact source-only Java classes for its dependency *names and signatures*, while **never using any original helper classfile**.

- The nonpublic original transform-component writer a(com/a/b/a/a) reads twelve float fields from the original adjacent math class and writes the exact 4x4 float array positions, inserting original zero/one homogeneous coordinates. After binding only original JVM class/field names, isolated Java9 javac matches **93/93 original JVM instructions and exact original offsets**, including every original field owner, float descriptor, array index and constant.
- The public vector-axis lengths output i():float[] independently instantiates three original 3-float vector helper objects (com/a/b/a/e) from original 4x4 matrix column array elements, invokes their original scalar-return method and writes the three results. Isolated Java9 rebuild matches **68/68 original JVM instructions/offsets and resolved field/method references**.

Together with the prior R150–R152 13 methods/350 instructions and R154–R155 three methods/281 instructions, this reaches **18 independently reconstructed original matrix Java methods and 792 matching JVM instructions** out of the original JVM class's 24 declared methods. Six original methods remain: its two Packet-dependent constructor/loader routines, plus four larger non-Packet matrix math and transformation routines.

**Key scope boundary:** The helper Java sources for com/a/b/a/a and com/a/b/a/e are PRIVATE **compile-only scaffolds** with exact original referenced fields/method descriptors, not accepted original implementations. In particular, the vector helper's scalar method body remains an unverified placeholder; the rebuilt matrix's correct invokevirtual instruction is real original-method Code evidence, but the helper's internal math/runtime behavior is **not verified or executed**. Original matrix selected-method JVM instruction parity is separate from StackMapTable representation, full original class ABI/method parity, client runtime equivalence and redistribution rights. Neither helper original binary is placed on javac classpath.

R157 cross-platform tests use independent synthetically compiled original rs.Game, ext.Transform, ext.Vector and ext.Matrix JVM classes, then separately compile selected matrix Java source with only helper source files. Verify that both selected matrix method JVM Code bodies match, while the unselected helper implementation is intentionally different and never accepted as original. Negative tests mutate matrix field indices, remove helper source, alter a helper method signature and change original JAR SHA. R156 and R155 tests also rerun.

Private original user binaries, original-derived Java source and experimental source-only helper files never enter public GitHub Actions or this public repo. Only synthetic examples, tooling and aggregate evidence are committed.

The original client's whole 1,271-Java-source normalized compilation error frontier remains independently observed at **516 errors**. The additional method recovery has not been integrated into a complete original Client/Packet source build, so no new compiler-error improvement or completion of recovered-source/v309/src is claimed.
