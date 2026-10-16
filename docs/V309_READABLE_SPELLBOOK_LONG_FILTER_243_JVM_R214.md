# R214 — original v309 long spellbook filter method Code from EXISTING readable Java

This batch advances original-client semantic source recovery using the ACTUAL, independently SHA-pinned decompiled source `rs/interfaces/widgets/Class179.java`. It does **not** invent a new spellbook filter implementation, insert new source into the private whole-client tree or claim a runnable client.

## Original-versus-readable proof

Original v309 JAR SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Original `rs/n/c/ap.class` SHA256: `b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4`.

Readable donor private source tree ZIP SHA256 `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`, exact decompiled `Class179.java` SHA256 `8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2` (34,978 bytes of original-decompiled Java).

**Original selected JVM method:** `rs/n/c/ap.a(rs/n/c/ap$c):void`.

**Existing readable source candidate:** `Class179.method2689(Class178):void`.

Unlike R212/R213, verbatim readable `method2689` does NOT yet reproduce the *compiler shape* of original Java 9 Code. The unchanged donor Java compiled successfully, but gave **242 JVM instructions** instead of 243. The difference is not different filtering behavior: it is one nested boolean guard compiled into a single late return, and seven `ArrayList`-typed calls emitted using `invokevirtual` rather than the original `List` `invokeinterface`.

The R214 verifier **requires the original donor method bytes unchanged before any adjustment**, then applies *exactly* these controlled source changes:

1. Convert the outer `if(field3646) { ... }` into logically equivalent `if(!field3646) return; ...`, retaining the original conditional inner block and all remaining operations.
2. Change `ArrayList var2 = new ArrayList();` to `List var2 = new ArrayList();` (same allocated instance and operations, different static interface type).
3. Change `ArrayList var3 = new ArrayList();` to `List var3 = new ArrayList();`.

The necessary removed outer-block closing brace is part of change 1. No predicate, call, loop bound, spellbook category, magic constant, skill-level condition or collection mutation is changed. **This is a compiler-normalized source candidate, NOT a verbatim unchanged-donor proof**; retain both hashes and the exact transformations.

SHA256 original unchanged donor method: `ec60c977992bb0e02ccba1a00e457f74cf30f135bd0eb8e5c2a5e89bf373ce27`.

SHA256 after the three compiler-shape normalizations: `f45d01c283418f7a48d5c923c6aedb230d61dcb88bd7ee16f8235cc70a3d4f15`.

## Direct original JVM Code parity

Using JDK 21 `javac --release 9 -g:none -proc:none -implicit:none`, with an EMPTY original/external binary and sourcepath and six *explicitly NONORIGINAL* separate compiler support declarations, the normalized real readable method compiles.

The independent original-vs-rebuilt `javap -p -c -v` audit establishes:

| Property | Original `a(ap$c)` | Recompiled `method2689(Class178)` |
| --- | ---: | ---: |
| JVM decoded instructions | **243** | **243** |
| Last instruction offset | **512** | **512** |
| JVM method `Code` bytes length | **513** | **513** |
| `max_stack` | **4** | **4** |
| `max_locals` | **13** | **13** |
| Method `ACC_PUBLIC | ACC_STATIC` | Same | Same |
| JVM operation, byte offset, branch target | **All exact** | All exact |
| Field/method/type operands | Original obfuscated names | **All 16 distinct renamed symbols accounted for** |

The original `List.add/contains/size` seven `invokeinterface` calls now have the exact original byte widths and their required instruction offsets. The full **243/243** aligned JVM instruction table was independently compared locally; no method was executed.

The public R214 verifier fail-closes on wrong JAR/source/method hashes, unknown original JVM symbolic references, changed branch/offset/operand, extra classes, missing class-owner/Code limits, or a fourth unapproved Java normalization. Its regression tests use wholly invented Java9 source and mutated code; the private source and client binary are never uploaded to public CI.

## Cumulative accepted selected JVM Code

| Research stage | Original spellbook method | JVM instructions |
| --- | --- | ---: |
| R212 | `h()`, `i()`, `j()` | 91 |
| R213 | `m(int)`, `k()` | 119 |
| R214 | **`a(ap$c)`**, now compiler-normalized | **243** |
| **Total selected original spellbook methods** | **6 of 14** | **453 matching instructions** |

The semantic readable widget superclass remains R210's **6 original methods / 11 instructions**.

The complete parent `rs/n/c/ap` has **eight other JVM methods** whose complete original Code parity from the existing source is not accepted here. Next focus on actual readable constructor, `register()`, UI creation and remaining static initializer, building under R125/R209 legal Java namespaces and preserving original source-provenance boundaries.

Whole-client v309 Java source still fails to compile; no new original-named Java was added to the pinned private full-client tree, so the last comparable source-only compiler frontier remains **1,295 Java files / 2,358 errors**. Full Recovery CI, runtime, complete JVM classfile identity, partial source helper implementation rights and redistribution authorization are not established. Keep PR draft.
