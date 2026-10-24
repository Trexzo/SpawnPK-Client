# Original v311 tile geometry — full `rs/I` JVM parity (dependency-stubbed, not accepted)

**Evidence date: 2026-10-22. Owner-authorized private source recovery.** Original input is the SHA-256-pinned user-supplied `client(20261021-111920).jar` (`5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`). Original binary, decompilation, reconstructed Java and original-class test harnesses remain **outside public GitHub**.

## New complete original-class JVM symbolic instruction reconstruction

Previously, **1,283 selected JVM instructions** of the original `rs/I` were reconstructed as Java9: 16 accessor methods (55), and the full static-array initializer (1,228). R58's next private milestone reconstructed the previously missing original **757-instruction constructor**. The constructor has **19 integer arguments**, constructs tile geometry for 13 tile types and four rotations, calculates faces/heights and fills original field arrays.

| Original `rs/I` member | Original ↔ source-built exact JVM instructions |
| --- | ---: |
| 19-integer constructor | **757/757** |
| Static initializer | **1,228/1,228** |
| 16 accessor/setter/getter methods | **55/55** |
| **Entire class** | **2,040/2,040** |

Exact equality includes declarations (**29 fields and 18 methods**), JVM descriptors, instruction order, byte offsets, branch targets, and resolved symbolic operands after normalizing only numeric constant-pool indexes. Original `rs/I.class` SHA256 is `94d14f52b4b3de8448753d5f40bae69bd5ad6a3649454a3e92801b42f03765b6`; the independently reconstructed Java9 class SHA256 is `948b4ce76a62c3748b60a001ac7e08d925022f0e2cb71a55c3e223caac1e7907`. **Full classfile byte identity is NOT claimed.** The v311 game binary was not on the compiler's classpath.

The independent private original-JAR-versus-source-built test ran **468/468 matching constructor behavior cases** (13 shapes × 4 rotations × 3 texture values × 3 distinct integer input patterns), comparing all 18 nonstatic fields and entire generated arrays. Both classloaders returned no constructor exceptions. Deterministic transcript digest: `1da28d8c471fba280c50cc7c5ce0b0d218f466fbca7c6d31eedc000d5dfe41f7`. All prior 11 static array fields matched, as did the earlier selected accessor behavior.

## Larger scene source build and strict acceptance boundary

The source-built `rs/I` replaced its old declaration-only stub in the privately reconstructed scene tile source group. **34 independently reconstructed original Java sources** now compile together with a completely empty original-client binary classpath: the previous 27 accepted-island classes, the six provisional tile classes `rs/H,T,U,l,m,n`, and `rs/I`. There are **exactly 36 Java9 compiler class outputs** because **two unrecovered source stubs remain**:

- `rs/a/a.class` — original scene-model superclass needed by several tile entity holders;
- `rs/k/e.class` — original renderer-flag provider needed by the `rs/I.g()` method.

All 33 previously compiled class SHA-256 fingerprints are preserved. All **4,160/4,160 original ordered symbolic JVM instructions** across the 34 genuine classes match in the expanded build. The now-seven-class tile frontier is **2,126 original matching instructions**; the prior 12-case original-vs-rebuilt scene tile behavior test also matches. The strict private verifier keeps both source stubs explicitly named and unaccepted.

**NO PROMOTION:** The accepted cumulative original-v311 source inventory remains **58 distinct classes / 3,261 matching instructions across separate previously certified builds**. The 2,040-instruction `rs/I` is a *full-instruction-parity source candidate*, but cannot count as **independently dependency-closed** while `rs/k/e` remains a source stub. The six other provisional tile classes still require the real `rs/a/a` source and its transitive dependencies. Source-closed `rs/H`, renderer `rs/V`, a fully independent 1,184-class game build, real-time rendering, and authenticated gameplay are not claimed.

## Fail-closed private reproducibility

The owner-private archive `SpawnPK-v311-R58-Tile-I-Full-Bytecode-34-Sources-Provisional.zip` has SHA256 **`cac9d3172c391ef98272a53249b3f0996251f5e48403e1ab863621cacc79201b`**. It contains **34 genuine Java source files + two explicitly marked Java stubs**, exact source/original/rebuilt SHA manifest, constructor and tile behavior probes, and a standalone verifier; it contains **no original JAR, original game classfiles, fonts or credentials**. Clean extraction and full re-verification passed. The separate refusal tests passed **3/3**: direct source SHA mutation, changed constructor JVM instructions even after both source and rebuilt-class SHA hashes were updated, and a wrong original input JAR hash.

Public CI exercises **independently authored synthetic Java9 sources only**, not these original game classes. Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **draft and unmerged**; no gameplay/manual runtime test is warranted for this private source-verification milestone.

**Next engineering gate:** reconstruct `rs/k/e` renderer-flag provider and `rs/a/a` scene-model dependency chain as authentic classes, remove both declaration-only source stubs, and rerun 34-source combined compiler/JVM/behavior validation before accepting any provisional tile class.
