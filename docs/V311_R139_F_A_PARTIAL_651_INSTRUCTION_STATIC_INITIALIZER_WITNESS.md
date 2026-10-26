# Original SpawnPK v311 — R139 PARTIAL rs/f/a 651-instruction method and initializer witness

**Date:** 2026-10-25. **Status: RESEARCH / PARTIAL ORIGINAL-SOURCE WITNESS, NOT AN ACCEPTED COMPLETE ORIGINAL JVM CLASS.** Owner-provided exact original-v311 client JAR SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Original `rs/f/a.class` SHA256 `01f0546471ba05b71cf4ceb8245f76fde9c3306375db41ef21323c8885d0281e`.

**The original client JAR, reconstructed owner-private Java source, compiler metadata transformer, private verifier/source ZIP, compiled original/rebuilt game/vendor binaries, game assets, credentials, hardware identifiers or account data are NEVER uploaded to this public repository.** This report contains only redacted aggregate source-certification evidence; the public test is entirely fictional.

## NEW original Java9 source progress: exact 213-instruction original static initializer

R138 previously certified eight individual genuine original method source witnesses (**438/438 original JVM instructions**) without accepting the full original class. R139 now also source-reconstructs the **ENTIRE original static initializer `<clinit>()` of `rs/f/a` with 213/213 EXACT original ordered JVM instructions**, symbolic referenced operands and exact original numeric byte offsets, without executable code patching.

| Authentically matched original-v311 member | Exact instruction parity |
| --- | ---: |
| `public rs.f.a();` | 3/3 |
| `public static boolean a();` | 2/2 |
| `public static boolean b();` | 2/2 |
| `public static boolean c();` | 2/2 |
| `public static void a(boolean);` | 20/20 |
| `public static void d();` | 4/4 |
| `private static void g();` — original complete settings writer | 364/364 |
| `public static void e();` | 41/41 |
| **NEW authentic `static {};` — original complete static initializer** | **213/213** |
| **Nine selected original member witnesses TOTAL** | **651/651** |

The original COMPLETE `rs/f/a.class` has **1,348 executable JVM instructions**. Its **697-instruction `public static void f();` settings reader remains ENTIRELY UNRECOVERED in the private candidate**, and the compiled research outer includes extra artificial helper methods and temporary enum owner types used only to compile from source. This is **NOT full source recovery, not a bitwise original classfile match, and NEVER a runnable/instalable genuine original `rs/f/a` class**. The owner-original `rs/u/a` class remains missing.

### Source compilation and original metadata semantics

Private one-shot `javac --release 9 -g:none -proc:none` accepts exactly **four reviewed private Java sources**: the incomplete owner candidate `rs/f/a.java` and the THREE previously independently accepted R125 callback source classes `rs/h/b,c,e`. **EMPTY javac classpath and sourcepath**; ZERO original `rs/` game binaries, ZERO vendor binary compiler inputs and ZERO fake implementations of other missing original game classes. All **3/3 R125 callback class SHA256 outputs remain byte-for-byte identical** to their individually accepted evidence.

To avoid the compiler's `ldc_w` / byte-offset drift in the source-generated initializer, R139 introduces isolated **early constant helper methods used only by the compiler**. These helpers are NOT original game methods or accepted class members. The resulting source-generated original method executable code has EXACT original offsets. Temporary enum aliases and a temporary local method stand in only for unresolved compilation symbols. On a COPIED output classfile constant pool, a strictly reviewed symbolic transformation restores **17 Fieldref and 6 Methodref original-owner targets**, including `rs/f/a$a`, `rs/f/a$b,c,d`, `rs/n/c/ap`, `rs/l/E`, and genuine still-unrecovered `rs/u/a.b():String`. It changes NO JVM executable `Code` payloads or exception handlers: **all 15 generated Code attribute SHA256 hashes are identical before/after restoration**. The original `rs/u/a` method is only a verified symbolic owner target, NOT an implemented method in this source island.

The candidate independently matches **ALL 49/49 owner-original `LambdaMetafactory` and `StringConcatFactory` `BootstrapMethods` argument entries**, including the original settings key-binding recipe and two original initializer string-concatenation recipes. Inspecting only visible `javap -c` opcodes is not sufficient for that semantic equivalence.

### Bounded certification: NO original or rebuilt game static initializer is run

The original and candidate `rs/f/a` static initializer, settings writer `g()`, settings reader `f()`, callback scheduling entrypoint, game networking/runtime and host operating-system identifier paths are **NEVER executed**. The original game JAR is opened solely for SHA/JVM declaration, bytecode, bootstrap and dependency reference comparison. NO settings-file reads/writes, network, external processes, shell commands, real machine-identity queries or gameplay tests. No original-vs-rebuilt runtime behavioral certification of a complete `rs/f/a` is asserted.

Original-v311 direct constant-pool references from `rs/f/a` include **ten OTHER original project class identities**. SIX are previously recovered: `rs/f/a$a`, `rs/f/a$b`, `rs/f/a$c`, `rs/f/a$d`, `rs/h/c`, `rs/n/c/ap$a`. FOUR remain unrecovered: `rs/V`, `rs/l/E`, `rs/n/c/ap`, and `rs/u/a`. The original `rs/f/a` ↔ `rs/u/a` direct dependency cycle remains a confirmed blocker. These counts are only direct reference coverage, NOT transitive source or actual game runtime closure.

### Independent clean-extracted private archive and fail-closed original tests

Owner-private R139 research ZIP `SpawnPK-v311-R139-F-A-Partial-651-Instruction-Private-Research.zip`: SHA256 **`1a652219d8122e56ca775ef10353dcd357fa55d389b4b88eed061a534375ddd4`**, **16,922 bytes / 11 unique entries**. Contains only incomplete private Java source, three previously accepted callback Java sources, pinned original/compiler manifests, COPIED-constant-pool restorers, strict method+bootstrap verifier, dependent original constant-pool auditor, fail-closed negative suite and README. ZIP contains **NO original client JAR, compiled original/rebuilt game/vendor binary classfiles, game assets, device IDs or credentials**, and remains OWNER PRIVATE, **NOT GitHub content**.

The R139 positive original-v311 SHA-JAR/source verification independently replayed from the **CLEAN EXTRACTED** private ZIP: original **651/651 exact method+initializer JVM instructions**, complete owner original symbolic owner references and byte offsets; **49/49 authentic bootstrap argument entries**; **15/15 Code payload SHA invariants**; **3/3 callback original accepted source-generated output SHA pins**; exact direct reference blocker audit, no original game/JVM initialization, and explicit status **`PASS_NINE_METHOD_WITNESSES_NOT_COMPLETE_OUTER`**. The negative suite **18/18 deliberately wrong candidates is designed to fail closed**, including manipulated source/manifest/reviewer tools/parent and original JAR authority, falsely claimed recovered original class / method / accepted cumulative totals, and genuine recompiled code changes with refreshed Java source/class SHA fingerprints. In particular, changed static-initializer boolean instruction, changed bootstrap prefix with identical visible bytecode, and wrong symbolic original method/field owner after refreshed metadata-restorer/source output hashes must all be rejected at original bytecode or bootstrap comparison rather than superficial SHA alone.

The PUBLIC [entirely fictional synthetic Java9 static initializer/bootstrap regression](../tests/test_v311_synthetic_static_initializer_method_witness.py) contains NO owner game Java, original constants or game IDs, and runs **3/3 locally passed** independent tests for repeatable Java9 compilation, changed JVM initializer code after rehashing, and changed invokedynamic bootstrap recipe with IDENTICAL visible `javap` disassembly. Toy static initialization is not executed. Hosted public CI does NOT have the private original-v311 source or original client binary and cannot independently certify the owner-original bytecode parity.

### Honest unchanged accepted recovery ledger

**Accepted cumulative DISTINCT original-v311 source recovery stays unchanged at 134/1,184 original class identities and 12,156 authentic matching original JVM instructions across separately verified accepted source islands.** The extra **651 partially witnessed original `rs/f/a` JVM instructions are NOT added** to this accepted count. The largest ONE accepted common compilation remains R136: **106 selected original-named JVM classfile outputs / 10,960 original instruction witnesses**, NOT a 134-class joint compilation.

Original complete `rs/f/a`, `rs/u/a`, `rs/n/c/ap`, scene model `rs/a/a`, renderer `rs/k/e`, previous enclosing-class/invalid enum `valueOf` metadata mismatch, complete game/client/network/native GPU/gameplay and host machine-identification execution remain UNACCEPTED.

[PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **MUST REMAIN DRAFT AND UNMERGED** absent specific user authorization. No manual gameplay or host machine-identity tests are requested.
