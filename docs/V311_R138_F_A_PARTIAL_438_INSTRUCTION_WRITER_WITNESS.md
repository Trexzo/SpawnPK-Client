# Original SpawnPK v311 R138 — PRIVATE 438-instruction PARTIAL `rs/f/a` method witness, NOT a recovered outer class

**Evidence date: 2026-10-25.** Owner-provided exact original v311 JAR SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`; owner original `rs/f/a.class` SHA256 `01f0546471ba05b71cf4ceb8245f76fde9c3306375db41ef21323c8885d0281e`. This public report contains aggregate/redacted **original-private evidence only**. No reconstructed game Java, game JAR, compiled game binaries, game assets, real device identifiers, owner-private metadata restorer, verifier or original-code ZIP is published.

## Significant PRIVATE original method-source reconstruction, but still NOT the original whole class

The R137 partial witness verified 6 genuine methods and 70/70 original JVM instructions. R138 source-reconstructs TWO MORE complete original methods: the `d()` scheduling method **4/4 authentic original JVM instructions**, and its target `g()` (complete private settings-writer method) **364/364 authentic original JVM instructions**.

| Verified original method declaration | Exact original ordered JVM instructions |
| --- | ---: |
| `public rs.f.a();` | 3/3 |
| `public static boolean a();` | 2/2 |
| `public static boolean b();` | 2/2 |
| `public static boolean c();` | 2/2 |
| `public static void a(boolean);` | 20/20 |
| **NEW** `public static void d();` | **4/4** |
| **NEW** `private static void g();` | **364/364** |
| `public static void e();` | 41/41 |
| **ALL EIGHT PRIVATE METHOD WITNESSES** | **438/438** |

Exact original-vs-generated `javap -p -s -c` matches each selected method's ordered instruction sequence, **numeric byte offsets, complete method declaration/descriptors and symbolic JVM operands**, with numeric constant-pool indices normalized. The 364-instruction `g()` is a substantial settings writer with writer operations, loops, conditional flags and temporary-file operations, but is **NEVER EXECUTED** in R138 verification.

**46/46 independently verified Java9 `BootstrapMethods` entries** are identical to the owner original, including the `rs/h/b` callback lambda's original `rs/f/a.g:()V` method handle AND each `StringConcatFactory` settings-format recipe. This prevents accepting a bytecode-instruction-only match with altered runtime string semantics.

The private **ONE partial Java9 `rs/f/a` source** compiles with **EMPTY compiler classpath and sourcepath**, alongside only the **three previously independently original-certified R125 callback Java sources** `rs/h/b,c,e`; their compiled classfile SHA256 hashes are **3/3 unchanged** from R125. ZERO original game/JAR or vendor binary compiler dependencies, zero fake source implementation of a missing separate game class. The partial source's compile-only nested enum owners and test-only static initializer are **DONORS and NOT real recovered game outputs**. A narrowly scoped COPY-only constant-pool transformer restores **seven** original symbolic `Fieldref` owner/name/descriptor triples (`rs/l/E.i`, `rs/n/c/ap.d/e/f`, and three `rs/n/c/ap$a` enum constants). **ALL NINE source-compiled executable `Code` attribute payloads, including exception handlers, are SHA256-identical before/after metadata retargeting: NO executable Code bytes changed.** The original game `rs/l/E` and `rs/n/c/ap` implementations remain unrecovered.

**IMPORTANT: The genuine full `rs/f/a.class` contains 1,348 JVM instructions. R138 recovers and proves only 438 instructions across eight selected methods. Its remaining 910 original instructions — especially the FULL original static initializer, settings reader `f()`, complete original fields, full external dependencies and original whole class runtime — are UNRECOVERED.** The partial test-only class must **NEVER** be installed as the game's real `rs/f/a`, nor counted as a distinct accepted original JVM class or as accepted cumulative original instructions.

### Strong private verification and safe boundaries

Owner-private research ZIP **`SpawnPK-v311-R138-F-A-Partial-438-Instruction-Private-Research.zip`**, **SHA256 `14ad44193a495b2bd51500fdb024afea6840cd8591d9388666fbf337ce05b607`**, **15,297 bytes / 11 entries**, contains reconstructed *partial* owner-private Java, the three already accepted R125 callback sources, strict fixed-hash manifest, COPY-only metadata transformer, method+bootstrap verifier, synthetic-only local Java probe, original dependency auditor, negative suite and README. **Contains NO owner-original client JAR, generated or original compiled game/vendor classfiles, game assets, account/device identifiers or credentials**. **This ZIP and all recovered game Java sources/verifiers remain OFF public GitHub.**

An **independent FULL CLEAN-ZIP-EXTRACTION replay** against exactly the SHA-pinned original JAR PASSED:

- **Eight methods / 438/438 original symbolic JVM instructions and exact byte offsets**, **46/46 authentic original lambda/concat bootstrap entries**, 9/9 Code payloads unchanged by metadata-only repair.
- **Three previously independently accepted R125 callback compiled-class SHA pins unchanged**, verified local Java9 source-only compiler classpath.
- **Ten harmless partial-candidate-local-only observations** (constant-false getters, keycode setup, isolated local boolean flag toggling). **Original owner-game `rs/f/a` class is NEVER initialized or executed; original-vs-rebuilt whole-class behavior parity is NOT claimed.** Real settings writer `g()`, save scheduling callback `d()`, settings file input/output, network/game/runtime and hardware fingerprint paths are **never executed**.
- **16/16 negative fail-closed cases** from the clean extraction, including changed/missing/unreviewed source and source/verifier/restorer/probe/audit tampering, false 135th-class ledger claims, false completed original outer, forged original authority and instruction credits. The most important cases are **REAL candidate recompilations AFTER BOTH altered Java SOURCE and rebuilt classfile SHA256 were repinned**: changed JVM boolean branch rejected by exact owner-original method instruction comparison, changed `StringConcatFactory` setting recipe with **identical visible JVM instructions** rejected by original bootstrap argument comparison, and a wrong `rs/n/c/ap` symbolic Fieldref owner after repinning the metadata restorer and rebuilt output SHA rejected by original symbolic instruction comparison.

The public [original-independent fictional Java9 writer/bootstrap regression](../tests/test_v311_synthetic_writer_bootstrap_method_witness.py) contains ONLY toy types, invented file contents and dummy strings, and **NEVER executes its toy writer**. **3/3 local tests passed**, covering repeatable bytecode, safe getters, a genuine changed instruction sequence, and differing runtime string bootstrap recipes with identical visible JVM disassembly. Public hosted CI is an independent safety check, NOT private original-v311 certification.

### Blocker graph and accounting stay honest

Original `rs/f/a` direct JVM project dependency audit STILL finds ten OTHER classes: six already accepted separately (`rs/f/a$a`, `rs/f/a$b`, `rs/f/a$c`, `rs/f/a$d`, `rs/h/c`, `rs/n/c/ap$a`), four remaining genuine original project references (`rs/V`, `rs/l/E`, `rs/n/c/ap`, `rs/u/a`). Real **direct `rs/f/a` ↔ `rs/u/a` dependency cycle** persists, neither original outer is yet recovered.

**Accepted cumulative DISTINCT source recovery remains UNCHANGED at 134/1,184 original-v311 classes and 12,156 matching original JVM instructions ACROSS separately authenticated source islands**, from R134. **The 438 partial-method instructions are NOT credited to the accepted cumulative 12,156.** Largest **ONE** original-named source-built group remains R136 **106 classfiles / 10,960 original JVM instructions**, unchanged by R137/R138 research. Original `rs/u/a`, `rs/n/c/ap`, scene model `rs/a/a`, renderer `rs/k/e`, nested owner reflection/invalid enum valueOf paths, full client/network/native GPU/gameplay remain NOT VERIFIED.

**Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) DRAFT AND UNMERGED.** No manual gameplay, host identity or settings-file exercise is warranted for this isolated method-only witness.
