# Original SpawnPK v311 R87 — 58-source rendering-state and bounded-map island

**Owner-private verification: 2026-10-23.** Exact owner-provided original JAR: `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Original game JAR, independently reconstructed proprietary Java, compiled original-name game classfiles and private JDK probes are **not publicly hosted**.

## Four new original-v311 source reconstructions

| Original class | Original class SHA-256 | Independent Java9-built class SHA-256 | Exact original symbolic JVM instructions |
|---|---|---|---:|
| `rs/n/d/a.class` — drawing-state record | `28892cba64d633c034ad0e278a427f756b8a82f4b923f357244d25de9ad4e0f3` | `f452e47fd5b0cc66ae0739e52811eba799ae5080b839152b9f4e313893fffeef` | **75/75** |
| `rs/l/u.class` — 512-entry bounded `LinkedHashMap` | `3a3f0e88ac4fbc73317b56b44921391fedb242af913e0da8c0f14f0af752a73c` | `a46e35a0c518aafec1c441c6ec73bd59113509594ad196cd396ad737927930d6` | **14/14** |
| `rs/l/e/d.class` — list-backed record | `dae2f2a146469286cd85036637e01e195f834682c4367b8e8067a69c507e5b04` | `453e43deb38daffa7f136d216bfc7880a7c22b28e315068395d30ddd4eb6aef3` | **20/20** |
| `rs/z/m.class` — Swing popup delegate | `b54794eb9e82776ed1c92a4939c1a2b8509e5e7435e658926e4ca9dca83fe894` | `5f03c43217457a30f4142d5013648fafc0f228e7f8430180d368f68d99917606` | **11/11** |
| **New original classes** | | | **4 classes / 120 instructions** |

All four classes are new relative to the 83-class certified original recovery ledger, not reintegrations of original classes already counted. All original-class field and method declarations/descriptors, ordered opcodes, exact byte offsets/branches and resolved symbolic operands match independently compiled Java9 source. Only numeric constant-pool indexes are normalized. Complete original binary classfile/StackMapTable/attribute equality and original source-text identity are **not** claimed.

## Closed 58-source build and bounded behavior checks

The **54 previously accepted R83 source files** and four new Java files compile **in one `javac --release 9 -proc:none -g:none` invocation**, without using the original client JAR or original game classfiles on the compiler classpath. The reviewed disposable compile-only alias for the original `rs/k/c` JVM class/package collision is inverse-restored in copied compiled classfile metadata. No canonical recovered source or original client JAR is modified.

The private verifier confirms **58 source-backed original-name Java9 class outputs**, **5,913/5,913 original symbolic instructions accounted for**, **54/54 old R83 compiled class SHA fingerprints unchanged**, **120/120 newly disassembled original-vs-rebuilt JVM instructions matching**, **zero declaration-only source stubs**, and **zero missing explicit original project-class dependencies**. The previously certified R83 5,793 instructions are retained by their identical emitted class hashes; they were **not all re-disassembled** in this faster milestone. Dependency closure is limited to classfile constant-pool and JVM descriptor type references, not dynamic reflection or assets/native libraries.

The bounded original-JAR-vs-Java-rebuilt headless JDK probe passed **30/30 new comparison cases** for nine-field rendering state, raw float bits and integer boundaries, 512-element insertion/access-order eviction, list-backed record mutations, and Swing popup wrapper class/method shape. It **did not invoke native window/popup display or verify visual appearance**. The earlier R83 48 behavior cases and R80's older 942 cases were not rerun here; do not report a fabricated 1,020-case new behavioral suite.

**Five/five private deliberate failure tests passed from the newly packaged archive after clean extraction**: altered source SHA, missing original source, wrong whole-JAR authority SHA, unreviewed compiler alias, and modified actual JVM getter instructions even after updating both reconstructed Java-source and independently compiled-class SHA pins.

Owner-private artifact: `SpawnPK-v311-R87-Scene-UI-58-Class-Private-Sources.zip`, SHA-256 **`e35024c7fe67daa0480b41f5d435624002933aaadcf451f7ca58f7c676d0f4b6`**. Archive has exactly **58 Java source files**, two private class-SHA manifests, a standalone verifier, bounded JDK probe and five refusal tests. **No original game JAR, original/compiled game classfiles, credentials, game assets or font binaries.** Never upload this owner-private recovered Java archive to a public GitHub repository.

## Distinct accounting and remaining gates

Prior accepted R83: **83 distinct original-v311 classes / 7,001 matching original JVM instructions**, cumulative across several certified source-build records. R87 adds **4 new / 120 instructions**, giving **87 distinct source-recovered original v311 classes / 7,121 exact original JVM instructions across separate independent source builds**. The **largest one-invocation source-closed group is 58 classes / 5,913 instructions**, not all 87 compiled together.

The independent public [synthetic-only state/map/popup test](../tests/test_v311_synthetic_state_lru_popup_source_parity.py) uses *unrelated* toy Java9 classes and exercises compilation, exact instruction parity, declared dependency closure, JDK-only behavior and refusal cases without any original game source.

Seven earlier tile candidates including `rs/I` still remain **provisional** and excluded because two substantial real original source dependency chains `rs/k/e` (renderer) and `rs/a/a` (scene model) are unrecovered. No complete 1,184-class source build, native/OpenGL rendering, full GUI behavior, live game login or server gameplay verification has occurred. Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**. Hosted CI of the synthetic-only changes must be checked separately.
