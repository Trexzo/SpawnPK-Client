# R160: independently rebuild two remaining non-Packet matrix methods

Scope: original v309 client Java recovery only, stacked on R159 #1050. This is a *partial* original matrix source reconstruction, not a completed client or authorization to publish original code.

## Original-v309 private evidence

The exact SHA-pinned original class com/a/b/a/b.class (SHA256 52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030) has two further method bodies independently recovered as Java 9:

| Original method | Exact original/rebuilt JVM instructions | Last bytecode offset |
| --- | ---: | ---: |
| c(Matrix), float-array matrix composition | 721/721 | 1126 |
| h(), determinant-based matrix inverse | 1566/1566 | 2393 |
| Total | **2287/2287** | |

The actual original JAR SHA256 is ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38. An independent private source-only javac --release 9 compile confirmed original operation order, offsets, float-array field and original member references in both methods. The inverse calls the already reconstructed determinant g():float. Both preserve local float temporaries before final 16 element assignments; no algebraic rearrangement was performed.

The original nine-method Java source ZIP is private (SHA256 25e6d126c4d1b94c04091a50ef9cd2084f69df33a00a68ab17d6d7b90d4a5669), as is its exact selection JSON (SHA256 cbf9fe6254a2451f957233f639e89d26d88ea0dffd83188cc14246b8a7639096). Together with seven earlier recovered R159 source method bodies, the nine-method private class recompiles with **3369 matching original instructions**, using three Java-only helpers with *unverified original behavior*.

The earlier method-level cumulative count was 20/24 and 1432 matching original instructions. R160 advances this to **22/24 and 3719 matching original instructions**, because its two newly reconstructed methods add 2287.

## New reusable source generator

R160 commits a SHA-pinned JVM float-local/array-mutator-to-Java candidate generator. It supports only precisely bounded this/argument field reads, indexed float-array operations, scalar float arithmetic (including unary negation), float local reads/writes, 16 array writes, and a precisely preauthorized same-owner float getter call. It fails closed on unknown instructions, branching, arbitrary invokes, unexpected fields, wrong original file hashes, and instruction-count/offset mismatch. Generated Java code is **private source candidate only** until independently compiled and checked against original.

Ubuntu/Windows CI compiles synthetic JVM method bodies, recovers Java statements through the new tool, recompiles using javac and compares fully resolved instructions against original, with negative hash and opcode-count tests. No SpawnPK original Java or binary is published to hosted CI.

**Remaining:** two original game Packet-dependent methods (constructor and loader), then complete matrix-source integration. No original game classfile was used as a compiler fallback. Neither full matrix behavior, Code/StackMap metadata, the original whole-client Java compilation, 516 previously observed full-source compiler errors, nor redistribution rights have been accepted or remeasured.
