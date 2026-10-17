# R192 — R12 full-source Java repair replay

Private source artifact: `SpawnPK_v309_FULL_SOURCE_R12_PRIVATE.zip`. It contains **all 1,274 Java candidate files**, per-file SHA-256 witness, and the full private compiler stderr. Only three files differ from R11:

| Java file | R11 SHA-256 | R12 SHA-256 |
|---|---|---|
| `rs/cache/osrs/util/Class49.java` | `ecd7cdc032e9bc9ef4b0de1a3f5de342a00dad1f91bf67537659e154f255fbf4` | `29c3aa15bde5da9063d4e6f66e8301f094537595505a87493200eeac5cf91266` |
| `rs/util/Class85.java` | `d541201d57d421e9fcde5c824895f2091fd9e5988b8f1bb9c345e15eeb9a7d17` | `bfc3a4db58f7bef99073dbb3f674878bc01efb0b534aef06018911ee28d1116d` |
| `rs/util/ExceptionHandlerCallable.java` | `36b6853d51b4868ffe6ad79d58b5a7db110c790b4820c4d7a2bcf5f64340e284` | `3151090bd7ebb3e9756a497714a9e17415feb56641cc97322ca518961a68844f` |

The edits remove Lombok `@SneakyThrows` from these three implementations. `Class49` now declares `IOException` on its I/O-owning methods; `ExceptionHandlerCallable.call` uses the `Callable.call throws Exception` contract; `Class85.method2500` uses a local generic rethrow for reflective checked exceptions without changing its declared method descriptor.

## Measurement

All 1,274 source files compiled together under the same JDK 21.0.12.1 no-third-party-JAR diagnostic profile as prior R11. **R11: 2,076 errors / 9 warnings. R12: 2,071 errors / 9 warnings.** Five fewer raw error diagnostics, not five independently verified original methods. The compiler still fails; no generated runnable v309 client is claimed.

**Important limitations:** `Class49` and `Class85` have many implicit dependencies unavailable under this profile, so isolated behavioral parity for them remains unverified. Adding checked declarations can change source-call-site compatibility and must be reviewed against the private owner graph. These are candidate repairs of a third-party decompilation, NOT original v309 JVM Code or ABI acceptance. Full 1,279-source private reconstructed snapshot replay remains outstanding. Private Java source is not committed publicly while redistribution rights are unresolved.
