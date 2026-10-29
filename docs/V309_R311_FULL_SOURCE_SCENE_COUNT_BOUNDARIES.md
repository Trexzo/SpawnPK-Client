# SpawnPK v309 R311 — complete recovered-source Scene count-boundary safety

Evidence dated 2026-10-26. This is the complete privately recovered **v309** source tree track, not the distinct v311 original-bytecode source certification track.

## What changed

One original-derived private production Java file was modified: `rs/Scene.java`. The original `Tile.field5058` storage contains **five** object slots, while `Tile.field5057` stores a separately mutable count. A deliberately malformed count of `Integer.MAX_VALUE` on the exact R310 compiled client caused **ArrayIndexOutOfBoundsException: Index 5 out of bounds for length 5** during `Scene.getInteractiveObject`. This is a deterministic offline fault injection; it does not establish that production gameplay naturally creates such a count.

R311 bounds reading loops to the five actual slots in scene queries, object metadata, plane transitions, decoration, lighting and selected draw traversal. It separately rejects invalid negative or fully occupied counts before scene insertion and preserves the original data when a removal encounters inconsistent count metadata. Two direct rendering-slot reads now skip null entries instead of dereferencing them. Normal valid zero-through-five slot semantics are preserved.

## Private full-source verification

- Parent R310 private ZIP SHA-256: `0bd0c412724a3a92409e78348c2fc81f58845a148c7286510e5b16f1ef48b223`.
- All original recovered source paths: **1,277/1,277** present and verified; `javac --release 11` generated **1,386** class files, zero errors.
- R310 JAR SHA-256: `ae8191810ad324b68495446e0da9f325157ccc719c1bc698a734643b8baba722`.
- R311 JAR SHA-256: **`b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721`**.
- New `rs/Scene.java` SHA-256: `c38fb283d7b2a6d21c0df6f0755c0608e39bfa9a157d56ef1e2ccd53e4109e94`.
- New `rs/Scene.class` SHA-256: `120d8a36711f154c12a09be383a23dfc52287fdfb29457f9b9183df4c218bf7e`.
- Exact compiled binary comparison: **1,385/1,386 existing class files unchanged**; only `rs/Scene.class` differs.
- Actual compiled private client headless regressions: **R311 37/37**, R310 **15/15**, R309 **38/38**, R308 **256/256**. Cumulative **346/346 PASSED**, without counting skipped tests.
- A clean independent ZIP extraction followed by complete source rebuild reproduced the exact expected R311 class-only JAR SHA-256.

The private cumulative `SpawnPK-v309-R311-Full-Recovered-Source-Private.zip`, size **22,212,587 bytes**, SHA-256 **`6089078c5b7d081a9677d2c5b0e9d5273d54189d60ded7b9e0a7b78d06dadb9f`**, contains the 1,277 Java sources, owner-private dependency JARs, compiled R311 JAR, full per-source SHA manifest, local rebuild helper and four regression sources. The archive is **owner-private and never uploaded to public GitHub**.

Public artifacts in this branch include only the exact [SHA-pinned R311 rebuild recipe](../tools/recovery/r311/rebuild_r311_from_pinned.py) and [original-independent fail-closed tests](../tests/test_v309_r311_source_only_builder.py). Hosted GitHub CI is separate from the private source/JAR regression; it does not prove game runtime or privately held source.

## Release boundary

No native Windows GUI/GPU or hardware rendering verification, original asset-backed `config.bin` regressions, authenticated production game-server session, sustained gameplay, or physical cache power-cut tests were executed at R311. Four earlier asset-dependent tests remain **NOT_RUN**, not passed. The source-compiled private client must not be called production-playable based on these headless checks.

Keep [PR #1143](https://github.com/Trexzo/SpawnPK-Client/pull/1143) draft and unmerged. Coordinate integration in [issue #1117](https://github.com/Trexzo/SpawnPK-Client/issues/1117); preserve the v311 exact-source project and the R310 rollback baseline.
