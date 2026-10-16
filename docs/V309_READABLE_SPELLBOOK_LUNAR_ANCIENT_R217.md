# R217 — original v309 lunar + ancient spellbook layout methods from existing deobfuscated Java

Client-side **original evidence / source parity**, stacked on [R216 draft PR #1103](https://github.com/Trexzo/SpawnPK-Client/pull/1103). The original v309 binary and readable decompiled Java were verified against the **exact** pinned private artifacts:

- Original JAR SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.
- Original `rs/n/c/ap.class` SHA256 `b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4`.
- Private recovered 1,295-Java-file source tree ZIP SHA256 `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`.
- Real existing readable `rs/interfaces/widgets/Class179.java` SHA256 `8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2`.

## Two complete original methods recovered from existing readable Java

| Original v309 JVM method | Actual readable source | Source SHA256 | Original instructions and final offset |
| --- | --- | --- | ---: |
| `rs/n/c/ap.p():void` | `Class179.method1712()`, source **unchanged** | `9a430b012fa327bdb563f1bf75e51409105b52ed279b801f2ffbe951d9c04f25` | **487/487**, offset **1050** |
| `rs/n/c/ap.n():void` | `Class179.method3532()`, two documented arithmetic compiler-shape rewrites | Original: `5c8eb43b2f81559ee70f0ef7fd16fac55be8cb9ae1e36b921f611670f70f1b54`; normalized: `72651ccaeba1dc34c6c9fc362420e535fc33a8894afbd9ff63c34c85534579ed` | **419/419**, offset **778** |
| **R217 total** | **Both actual readable-source methods** | | **906/906** |

The lunar method `method1712()` defines lunar spellbook child positions and can be recompiled verbatim. The ancient method `method3532()` creates spell widgets and arranges their child positions. Its unchanged readable donor produces 425 JVM instructions; its source logic matches, but Java 9 emits two addition/temp-store sequences instead of the original `iinc` instructions. Two precise arithmetic-equivalent compiler-shape source transformations are therefore allowed, and required:

```java
// Original decompiled Java source
var8 = var6 + 4;
var9 = var7 + 2;

// Original-v309 JVM compiler-shape equivalent (same incoming var8=var6, var9=var7)
var8 += 4;
var9 += 2;
```

With those **two and only two** source edits, the compiled ancient method exactly matches all 419 original JVM instruction offsets/opcodes/branch targets. Unlike R216, this method is explicitly a *compiler-normalized* readable source candidate rather than verbatim source-Code parity. The original and normalized snippet hashes are both pinned and rechecked; any additional change fails.

An independent isolated JDK21 `javac --release 9 -g:none -proc:none -implicit:none` build with empty original/external classpaths and **three nonoriginal compiler-only declaration classes** emits both selected methods. Original-vs-rebuilt `javap -p -c` compared **every instruction row and referenced symbolic operand**: lunar needs three owner/field/method aliases; ancient needs eight. Exact common constants, arithmetic and loop control offsets match. The verifier additionally compares method access flags, full Code byte lengths (1,051 and 779), max stack and locals, exception handlers and StackMapTable presence.

The three fake declarations are only used to make the chosen original-decompiled methods compile in isolation. They **are not** original reconstructed Java or added to any full source tree. No game code is executed; class binary identities differ by the explicitly readable naming.

## Where this brings the project

| PR | Selected original spellbook method Code recovered | JVM instructions |
| --- | --- | ---: |
| R212 | `h,i,j` | 91 |
| R213 | `m(int),k` | 119 |
| R214 | `a(ap$c)` | 243 |
| R215 | `<init>,<clinit>` | 17 |
| R216 | `l` | 160 |
| **R217** | **`p,n`** | **906** |
| **Total** | **11 of 14 original spellbook JVM methods** | **1,536** |

Three method bodies still need to be verified from the existing `Class179.java` donor: original `a()` ↔ readable `register()`, original `m()` ↔ readable `method2352()`, original `o()` ↔ readable `method892()`. These are large UI composition bodies and may require additional compiler-shape normalizations, but all changes must be explicitly source- and bytecode-proven, not guessed.

The dedicated hosted Ubuntu/Windows regression tests use **unrelated synthetic Java9 source**. Negative tests change array-loop conditions, child-offset arithmetic, source input fingerprints and symbol mappings, proving that the public matcher rejects deviations. The private original source/JAR stay off GitHub and off Actions.

**Not accepted:** the original 14-method parent as one complete Java class, legal global v309 class/package mapping, runtime execution, source redistribution rights, original classfile byte identity, any full-client compiler improvement. The last comparable controlled complete-client JDK-only source build remains **1,295 Java files with 2,358 compiler errors**. Keep the PR draft pending complete source/mapping integration and private-input verifier replay.
