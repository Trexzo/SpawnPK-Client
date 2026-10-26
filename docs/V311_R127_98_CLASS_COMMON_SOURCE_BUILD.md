# Original SpawnPK v311 R127 — owner-private 98-class integrated Java9 source build

**Evidence date:** 2026-10-24. Original owner-provided v311 client JAR SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The owner-private recovered Java sources, original JAR, private compiler, verifiers, compiled game/vendor classes, game assets and account data **remain outside public GitHub**.

## R127 integrates FOUR already accepted R126 classes into ONE source build

A **single `javac --release 9 -proc:none -g:none` invocation with 92 owner-private Java source files** produces **98 selected original-named classfiles / 9,889 accounted original matching JVM instructions**. The prior R124 common build produced 94 / 9,153. All **94/94 prior R124 original-named rebuilt classfile SHA256 fingerprints remain byte-for-byte unchanged**.

| Previously R126-accepted original JVM output | Original ordered symbolic JVM instruction parity | Same source-generated SHA256 as independent R126 |
| --- | ---: | --- |
| `rs/n/c/ap$a.class` — spell categories | **50/50** | `296f58413e85cde83941c4d7d2ac589a6207614cfb03e12f8b5e4f9da7856991` |
| `rs/n/c/ap$b.class` — 41-entry spell table with lookup | **586/586** | `7b9cdeeed9a59496d78a65a019b46b9afdfe682e3996d6ac915892e7139a15a8` |
| `rs/n/c/ap$c.class` — spellbook modes | **50/50** | `4a64b3679d60cfe3e8645d73876b5049665a88e1f7040f50991b47f37fd2805b` |
| `rs/u/a$a.class` — direction modes | **50/50** | `2f72806cced4e8160a536d332f8b018c7cfa1159e049ac6328cc7649dac3b583` |
| **Integration of FOUR existing R126 source-recovered classes** | **736/736** | **4/4 identical rebuilt hashes** |

Two temporary Java compiler donor outer classes `rs/n/c/ap.class` and `rs/u/a.class` are **DISCARDED** and **NEVER represented as genuine recovered original outer implementations**. The prior unrelated temporary renderer / environment / switch-map donor owners remain discarded. R126's original nested/obfuscated member identities are restored on copied JVM constant-pool/metadata only; the exact **raw Code and exception-handler attribute SHA256 sets are unchanged**. No invented game implementation source stubs or original `rs/` game binary classes were used in the Java compiler classpath. The ONLY binary compiler inputs are authenticated original-owner-JAR-derived **vendor** Trove/Google/LWJGL/javax.inject classfiles, never uploaded publicly.

The exact original-vs-rebuilt `javap -p -s -c` declaration, method/field descriptor, offsets, opcode and symbolic operand comparison passed **736/736** for the four newly integrated outputs; each matches the same rebuilt SHA pin from the independent R126 private source island. We do not assert full original classfile byte identity or original author-authored Java text.

### Freshly extracted owner-private ZIP replay

The private `SpawnPK-v311-R127-98-Class-Private-Integrated-Sources.zip` was assembled with **184 exact selected entries**, without compiler outputs, binary resources or owner JAR, and independently clean-extracted. **SHA256 `4ab8d1da6bba8b722df663a201806fd090ad7de0e76b015dba8973902f6f3273`**, **326,912 bytes**. Its private manifest binds all **92** Java sources, 15 critical compile/probe/helper files, previous R124 manifest and R126 accepted class manifest, the exact owner JAR, 94 prior compiled outputs and the four R126 output SHA pins. The archive itself remains off public GitHub.

From that clean extraction, a fresh `javac` source rebuild passed exact **98/98 selected output identities**, **94/94 previous rebuilt SHA pins unchanged**, **4/4 R126 compiled SHA pins unchanged**, and new integration's **736/736 original-vs-built symbolic JVM instructions**. Seven bounded original-owner-JAR vs rebuilt probes also passed:

| Bounded private probe | Original matching observations | Original owner JAR in rebuilt runtime? |
| --- | ---: | --- |
| R111 overlay | **65/65**, plus case-count sentinel | No |
| R120 scene callbacks | **20/20** | **Trailing metadata-only fallback** |
| R114 UI enums | **20/20** | No |
| R117 scene-node behavior | **24/24** | No |
| R116 renderer mode | **17/17** | **Trailing metadata-only fallback** |
| R123 environment enums | **53/53** | **Trailing metadata-only fallback** |
| R126 spellbook/direction enums | **63/63** | **No fallback** |

The original game JAR is used for the independent original baseline runs, original class SHA and bytecode parity, and only as trailing **RUNTIME-ONLY** metadata fallback where explicitly stated. **Never as javac original-game input.**

An independently clean-extracted `negative_r127.py` run passed **9/9 fail-closed refusals**: edited/missing/extra unreviewed source, changed compiler or metadata transform or probe, inflated distinct recovery ledger, wrong original JAR and a **REAL reordered spell initializer** with Java-source SHA, compiled class SHA and R126 manifest SHA **all deliberately repinned consistently**. That last case passes the hash preflight but is rejected by `ORIGINAL_JVM_PARITY_MISMATCH rs/n/c/ap$b.class` against the owner-original bytecode.

### Scope exclusions and accounting

**Distinct recovery ledger remains UNCHANGED: 129 / 1,184 accepted original-v311 JVM identities and 11,206 matching original JVM instructions ACROSS separately privately certified source builds.** R127 adds ZERO newly accepted distinct identities or instruction witnesses; it improves only the largest ONE compilation from R124 **94/9,153** to **98/9,889**. Do not imply all 129 classes compile together.

Importantly, R126's **reflection mismatch remains**: `getEnclosingClass()` and invalid `valueOf` exception paths for the R126 nested spellbook/direction classes were previously observed to be non-parity/incompatible with the unrecovered outer owners. Those cases are deliberately **excluded** from the 63/63 bounded functional observations and remain **UNACCEPTED** in R127. Neither original outer `rs/n/c/ap` nor `rs/u/a` is source-recovered; the original `rs/f/a` parent remains an actual missing direct dependency (6/11 direct accepted), original scene model `rs/a/a` remains 7/14, original renderer `rs/k/e` remains 17/36. Seven provisional tile classes and full game source build, native/GPU rendering, complete Java runtime/gameplay and bitwise original classfile identity remain unverified.

[Public synthetic-only Java9 regression](../tests/test_v311_synthetic_spellbook_common_build.py) uses ONLY invented Java class/enum/value names and entirely fictional IDs, and independently exercises one-build previous-output stability, discarded donor owners, deterministic 41-entry enum output and genuine JVM initializer change after candidate source/class hashes change. It has no original binary or recovered Java source. **Hosted public CI is a separate original-independent safety test, not the owner-private original JAR certification**.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT AND UNMERGED**. No manual gameplay test is necessary for this source-only integration stage.
