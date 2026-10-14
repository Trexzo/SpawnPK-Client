# R164 — fully restore an original vector-helper Java class

Client-only, original v309 recovery. Stacked on R163 #1054; source milestone #1004.

## Independently verified original v309 Java reconstruction

The original matrix already compiles from recovered Java (R162: 24 methods, 3,780 original JVM instructions). Its helper com/a/b/a/e.class, previously represented only by an **unverified compiler-only Java scaffold**, is now independently reconstructed as a complete original-named Java class.

Original e.class: **999 bytes**, SHA256 **64f3e4ee692bb549129e2a41342beae83ac94edd28296b88a7694777268334b0**. Original Java method inventory: constructor, empty static method, scalar 3-component length using Math.sqrt, formatted toString, static initializer; **5 methods, 3 float fields**.

A real private Java9 javac --release 9 -g:none -proc:none build, using ONLY the Java standard library, independently compiled source which matches **all 80/80 original decoded JVM instructions**, offsets, original field and method references, float-operation order, StringConcatFactory invocation, and all five method signatures. Both class files are 999 bytes, but their SHA digests differ: the rebuilt class is **0d600f93a69fa1bee79b6debfda5b710b0337a739360cd6dee64b9394c3cc4c1**. Same size and Code instructions do NOT prove byte-identical full classfile metadata or automatic runtime equivalence.

The previous 1,272-file private client source tree is extended with exactly this one **real source-reconstructed helper Java**, to **1,273 files** at recovered-source/v309/src/. Original 1,272 source files stay unchanged. The other four helper types (especially original rs/x/e Packet) remain **unverified and excluded**.

Private pins:
- Original whole v309 JAR SHA256: ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38
- Private full original e Java ZIP SHA256: 3a35cc1c1246a7d4f30b3bc8732540db6d3dc0c312d7ebd46a5bd4c1fc8f2d54
- Private original-name e Java source file SHA256: fe2e0642aa2ed5427ad7d1273e901499483bd750b1b8fa1f72e2b922e4e1cc0f
- Prior 1,272-file source tree ZIP SHA256: e4832383e0484af0b5e73f403f4740d8ad5fc8aeee4ad574a97b0c6cb589d66a
- New 1,273-file source tree ZIP SHA256: **758ea72c391a02bd0fc4762d26e0fdef32af44bea0b342589f1139c77874516a**

## First independently measured whole-client compiler reduction

Same trusted JDK21 using javac --release 9, annotation processing OFF, empty original/external classpath, all source files explicitly listed, max errors 10,000:

| Private input | Actual javac diagnostics |
| --- | ---: |
| 1,271 original candidate Java files | 2,391 |
| + recovered matrix class (1,272) | 2,364 |
| + recovered vector e Java (1,273) | **2,358** |

These are independently rerun JDK-only source diagnostics, with no original client binary fallback. The matrix addition reduced net errors by 27; the real vector source reduced a further 6. This is NOT directly comparable to the earlier **516**-error frontier, which used a provisional normalized binary classpath; it does not mean the full 1,273-file client compiles yet.

## GitHub code, private evidence and CI

R164 adds a full original-JAR-versus-isolated-Java verifier with SHA-pinned original class/source, full method identity inventory, all original field names/descriptors/access flags, complete 80-instruction method Code (stack/locals/branches/handlers and resolved references), self-call closure and separate StackMap reporting. It only accepts a single independent original Java source owner, compiled with empty project/original binary classpath. Its source-tree overlay operation checks the private 1,272-file tree SHA, rejects overwrites or casefold collisions and preserves every previous file exactly. A separate pipeline runner requires vector Code proof BEFORE overlay.

Ubuntu and Windows CI use only synthetic vector classes (with deliberately altered arithmetic and field layout negative tests), plus synthetic source-tree preservation tests, and rerun the R163 integration regression. No original user Java or JAR bytes enter public GitHub.

**Still missing:** the other original class helpers com/a/b/a/a, c, d and original Packet rs/x/e, and full client source namespace reconciliation. Full 1,273-file source tree is still not independently compilable. The source and original JAR stay PRIVATE pending provenance/rights. Exact official GitHub R164 private CLI replay remains distinct from the independently performed original Java9 disassembly and JDK-only compiler audits recorded here.
