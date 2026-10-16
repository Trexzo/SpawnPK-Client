# R218 — complete original-v309 lunar spell-definition method from unchanged readable Java

Stacked on [R217 draft PR #1104](https://github.com/Trexzo/SpawnPK-Client/pull/1104). All source behavior was found in the EXISTING deobfuscated v309 client source; this stage does not invent a duplicate method implementation.

## SHA-pinned original and donor evidence

- Original v309 client JAR SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.
- Original `rs/n/c/ap.class` SHA256 `b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4`.
- Private existing recovered 1,295-Java-file source ZIP SHA256 `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`.
- Original-decompiled readable `rs/interfaces/widgets/Class179.java` SHA256 `8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2`.
- Complete, **unchanged** `Class179.method892()` Java source-body SHA256 `aecd4c7af25cff1dd4b2f04a7dbdd39f89b7fe215b2d941588f80fe82d512c6d`.

The complete original `rs/n/c/ap.o():void` method is already represented by the readable `Class179.method892():void`: it defines lunar spell buttons, rune requirements and descriptions, and calls the separately established lunar-layout method `method1712()`.

## Direct source-to-original JVM proof

An independent real original JAR `javap -p -c` comparison against isolated `javac --release 9 -g:none -proc:none -implicit:none` of the unchanged donor body showed:

| Evidence | Original `o()` | Rebuilt readable `method892()` |
| --- | ---: | ---: |
| Decoded JVM instructions | **760** | **760** |
| Last bytecode offset | **1643** | **1643** |
| JVM method Code length | **1644 bytes** | **1644 bytes** |
| Instruction offsets/opcodes/control flow | exact | exact |
| Original owner/field/method symbolic aliases exercised | **8** | all covered |

The original deobfuscated Java source is **not edited**. The original→readable eight required aliases explicitly cover the call to original `p()` ↔ `method1712()`, lunar-home teleport button, lunar-rune overlay, font array field, three-requirement spells, two-requirement spells, alternative lunar spells and offset lunar spells. All other JVM symbolic operands, magic constants, strings, branch targets, Code attribute limits and method flags must match unchanged.

The standalone Java9 class compiles against only TWO isolated NONORIGINAL compiler-only helper declarations: `Widget` with correct static lunar-builder signatures and `HitsplatFont`. It contains a NO-OP `method1712()` signature purely to satisfy the compiler; R217 separately verifies the **real** `method1712()` Code, and the R218 fake is not recovered original code. No original JAR classes are present on the compiler classpath. No game method is executed.

Public GitHub provides the SHA-pinned actual-original-input verifier, strict full 760-row JVM Code comparator, complete source/JVM provenance, and unrelated invented synthetic Java9 regression tests. Hosted tests reject altered loop predicates, wrong call targets, changed member-alias maps and forged binary input. Hosted Ubuntu/Windows Actions do not receive original-derived Java or binary data.

## Cumulative original parent recovery from the REAL readable source

| Research PR | Original method(s) | Original JVM instructions |
| --- | --- | ---: |
| R212 | `h,i,j` | 91 |
| R213 | `m(int),k` | 119 |
| R214 | `a(ap$c)` | 243 |
| R215 | `<init>,<clinit>` | 17 |
| R216 | `l` | 160 |
| R217 | `n,p` | 906 |
| **R218** | **`o`** | **760** |
| **Total** | **12 of 14 original `rs/n/c/ap` methods** | **2,296** |

The only remaining two parent method bodies are original `a():void` ↔ readable `Class179.register()` and original `m():void` ↔ readable `Class179.method2352()`. These contain substantial widget image and classic-spellbook setup, respectively.

The last comparable full-client source-only Javac frontier is still **1,295 Java files / 2,358 errors**, because neither the existing readable Java donor nor these compiler-only declarations have been inserted as duplicate original-named code in the private source tree. Full class/source-tree compilation, runtime, original v309 classfile binary byte identity and redistribution rights remain open. Keep draft until exact private source verifier replay, dedicated CI and whole-source acceptance.
