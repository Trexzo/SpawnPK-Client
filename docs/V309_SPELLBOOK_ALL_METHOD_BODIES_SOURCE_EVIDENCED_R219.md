# R219 — All 14 original v309 spellbook method bodies individually source-verified

Client-side original-v309 source-deobfuscation milestone, stacked on [R218 PR #1105](https://github.com/Trexzo/SpawnPK-Client/pull/1105). The objective is to prove original **JVM Code** is represented in the ALREADY EXISTING readable `rs/interfaces/widgets/Class179.java`, rather than adding a duplicate original-named source reconstruction.

## Exact private original and readable-source evidence

- Original v309 JAR SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.
- Original `rs/n/c/ap.class` SHA256 `b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4`.
- Private decompiled v309 1,295-Java-source snapshot SHA256 `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`.
- Actual preexisting `rs/interfaces/widgets/Class179.java` SHA256 `8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2`.

The **last two previously unverified original Java method bodies** are now independently compiled from the preexisting readable source with their bodies unchanged:

| Original JVM method | Original-decompiled readable source | Verbatim Java method SHA256 | JVM instructions / final offset |
| --- | --- | --- | ---: |
| `rs/n/c/ap.a():void` | `Class179.register()` — category initialization, widget registration, texture/sprite data and teleport metadata | `d9ae9d22316b6780946ae471b051a2cbe8634194353cb3881681acdb11e80279` | **438/438**, offset **1030** |
| `rs/n/c/ap.m():void` | `Class179.method2352()` — classic spellbook UI and magic spell definitions | `3b51bad51c32fa622aab39fbc694e3804080b03ec634207c7702e85b7f6dce31` | **1,580/1,580**, offset **2726** |
| **R219 total** | | | **2,018/2,018** |

For each source body, I locally rebuilt an isolated Java 9 class using `javac --release 9 -g:none -proc:none -implicit:none`, with empty original/external classpaths. Two separately defined NONORIGINAL compiler-only dependency snapshots are used to prevent guessed runnable behavior: `register()` needs a temporary Sprite/WidgetComponent/Class176 ABI, while `method2352()` needs the classic spell/UI builder signatures, widget scripts and child arrays. The real method bodies are never edited. Original game classes are NOT on the compiler classpath; no original or candidate method is executed.

Independent SHA-pinned original JAR vs recompiled-source `javap -p -c` comparisons show every original opcode, byte offset, branch target, integer/string constant and old-to-readable symbolic operand matches: exactly **21 original member/owner aliases for registration** and **23 for classic UI construction**. The R219 public verifier also checks per-method access, Code byte length (1,031 and 2,727), max stack and locals, handler regions and StackMapTable presence. Unknown original symbolic references and altered donor method hashes fail closed.

## Complete individual-original-method inventory

| Research batch | Verified original method(s) | Original JVM instructions |
| --- | --- | ---: |
| R212 | `h()`, `i()`, `j()` | 91 |
| R213 | `m(int)`, `k()` | 119 |
| R214 | `a(ap$c)` filter predicate and state (three documented compiler-shape rewrites) | 243 |
| R215 | `<init>`, `<clinit>` | 17 |
| R216 | `l()` filter panel layout | 160 |
| R217 | `n()`, `p()` ancient and lunar layouts (two documented compiler-shape rewrites in `n()`) | 906 |
| R218 | `o()` lunar spell definitions | 760 |
| **R219** | **`a()`, `m()`** registration and classic spellbook | **2,018** |
| **TOTAL** | **14/14 original JVM methods** | **4,314 matching decoded JVM instructions** |

The independent R210 original abstract widget superclass proof provides **6/6 methods, 11 JVM instructions**, from the existing readable `Widget.java`. R211 supplies a pinned crosswalk for all 14 spellbook parent methods and 14 fields, including constructor and initializer.

## Critical boundaries — what is and is not complete

**Completed:** individually verified source-semantic JVM Code for **every original method body** of `rs/n/c/ap`. The relevant readable implementations are already present in `Class179.java`; reproducing source behavior does not require creating new duplicate original-name Java source.

**NOT COMPLETED:** one **whole `Class179.java` class compiled in a single source-only build** with all 14 methods at once. Isolated method compilations use separate deliberately fake source declaration helpers, which cannot be treated as recovered original implementations or added to the accepted private client source tree. Constant-pool ordering, Java 9 `ldc` vs `ldc_w`, JVM StackMapTable representations and cross-owner linkage may differ when all 14 method bodies are compiled together. Original binary byte-for-byte classfile identity has not been proven. Full original v309 client compile and runtime remain unverified.

**Next engineering milestone:** build the full readable `Class179.java` source together with the separately verified `Widget.java` base and stable legal Java source names, using real decompiled dependency owners whenever available; isolate remaining unresolved true dependencies rather than inserting fake behavior into the permanent source tree. Run complete all-14-method Code parity from that *single emitted class*, then the source-tree compiler and runtime checks. Only an actual shared-source compiler run can update the previous comparable JDK-only whole-client frontier: **1,295 Java files / 2,358 errors**. Do not claim a reduction in that number from isolated method proofs alone.

GitHub Actions Ubuntu/Windows synthetic tests contain unrelated invented Java9 source and reject changed branch predicates, array initialization, missing/duplicate methods, incorrect alias/descriptor maps, forged original JAR hashes and changed source provenance. Original-derived Java/JAR never enters public CI; publication rights and runtime compatibility remain open. Keep PR DRAFT until the full class and client compilation gates are accepted.
