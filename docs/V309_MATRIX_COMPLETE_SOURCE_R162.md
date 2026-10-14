# R162 — assembled original-v309 matrix Java source (24/24 methods)

Client-only recovery, continuing R160 #1051 and R161 #1052. Full client source milestone #1004 remains open.

## Private original-v309 outcome

The exact original v309 matrix owner com/a/b/a/b.class is 8,172 bytes, SHA256 52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030. It has **24 JVM methods** including constructors, pooling and class initializer, math/inversion, and Packet-dependent constructor/loader.

All previously reconstructed implementations have now been combined into **one original-named Java class**. Its independent Java 9 compilation used only five source-only helper classes, including a placeholder original-named Packet type; NO original client/class binaries were supplied on the compiler classpath.

Original-versus-rebuilt private JVM disassembly matches **all 24 methods and all 3,780 decoded instructions**, with the same offsets, operations and resolved references. A real Java name collision was fixed: original field d:int shadows the original helper class d, so the static helper invocation in the Packet loader needed a fully qualified class name. This did not change its JVM invocation.

Pinned private artifacts:
- Full original v309 JAR SHA256: ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38
- Recovered 24-method Java ZIP: fd2c330c8cdadb5c5f5c8640e624b566395eca589386a272933cc04da93a56
- Five source-only Java helper ZIP: d5a346413ceee1a0a657923df9750a80beb31be933ff708415621b7d812e3c3e
- All-24 original method selection JSON: 943d83fef1402cd3e15081a03ee4f0c3815a5055ad8ed860ab3decfa4f2a517c

No original binaries, recovered source text or helper implementations are committed to public GitHub.

## GitHub R162 acceptance

New private verifier checks complete method identities including all constructors and class initializer, field name/descriptor/access ABI, **3,780** instruction matches, and **12** same-owner method invocation edges all satisfied by selected source implementations. Source-only compilation requires exactly one game-owned original Packet Java type and four non-rs original-named helper Java types; each original identity must occur in the pinned JAR. It rejects helper binaries, unknown classes and mutated SHA-pinned inputs.

Ubuntu/Windows synthetic CI checks full source compilation with game-linked signatures, changed method and field mutations, missing initializer and helper SHA rejection. Hosted CI contains synthetic source only.

## Unfinished

**24/24 matrix method instruction recovery is not 24/24 verified dependencies or full-client source recovery.** The Packet and auxiliary Java scaffolds provide compiler signatures but their method bodies have NOT been reconstructed/validated here. StackMap and full classfile attributes are separately assessed. Complete original v309 client compilation has not been rerun; the previous independent 1,271-Java candidate frontier was 516 errors on a provisional dependency capsule. No new error reduction or original source-redistribution authorization is claimed. The exact R162 private CLI replay remains distinct from the independently performed disassembly comparison.
