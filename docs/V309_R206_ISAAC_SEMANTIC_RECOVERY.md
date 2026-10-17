# R206 — semantic source recovery of ISAAC packet cipher

The uploaded private v309 client contains `rs/network/Class257.java`, an independently compiling ISAAC PRNG/cipher implementation. This private pass replaces eight obfuscated implementation identifiers with semantic names: `remaining`, `results`, `memory`, `accumulator`, `lastResult`, `counter`, `generateNextBlock`, `initializeState`. It retains the original public `method0()` selector and constructor so existing callsites retain source compatibility, and adds a `nextInt()` alias.

**Actual Java 11 validation:** Compiled the original and edited `Class257.java` separately under `javac --release 11`. Executed a 4,096-integer ISAAC output stream from fixed seed `{1,2,3,4}` for both implementations. The complete outputs matched byte-for-byte; SHA-256 of newline-separated decimal output: `60df10cc71daf3c9322e9e33a98c989492628f64dc06038c932d3f851934aa9c`.

Private before SHA-256: `b41c145718684053a0820a4af0a45d7bc1e028b0167953e963cafa0fabe6b568`. Private edited source SHA-256: `be96327ef802cc9b61501daa53583cdb0104c5d1924f2bc7270529d2ddbfb196`. Full 1,274-source candidate ZIP `SpawnPK_v309_R206_FULL_SOURCE_SEMANTIC_PRIVATE.zip` delivered privately; only this one class changed. The last unchanged-tree Java11 dependency-free compiler check reported 2,001 errors. No full-client build or exact original binary method equivalence is established from the ISAAC stream test.

This is **source-level deobfuscation and behavior-preserving refactoring of a real client class**, not another build-report-only change. Public GitHub stores the evidence, not the original-derived Java bytes. Caveat: adding a public `nextInt()` method alters API surface; this is not exact-original classfile or ABI parity.
