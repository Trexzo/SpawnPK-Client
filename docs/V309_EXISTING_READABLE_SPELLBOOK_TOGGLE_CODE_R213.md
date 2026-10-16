# R213 — prove original spellbook m(int) / k() JVM Code from existing Class179 Java

Original v309 CLIENT semantic source reconstruction, stacked on [R212 PR #1099](https://github.com/Trexzo/SpawnPK-Client/pull/1099), [R211 #1098](https://github.com/Trexzo/SpawnPK-Client/pull/1098), and [R210 #1097](https://github.com/Trexzo/SpawnPK-Client/pull/1097).

## Exact original and source evidence

Pinned v309 full original JAR:
`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

Original `rs/n/c/ap.class` SHA256:
`b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4`.

Existing private readable decompiled `rs/interfaces/widgets/Class179.java` (34,978 bytes) SHA256:
`8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2`, from SHA-pinned private R203 1,295-file source ZIP:
`cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`.

The two methods below are extracted VERBATIM from that exact existing Java source (source SHA and each method-body SHA independently pinned) and compiled with `javac --release 9 -g:none -proc:none -implicit:none` using an empty original/external binary classpath.

| Original method | Existing readable source method | Original JVM instructions | SHA256 of verbatim donor Java method |
| --- | --- | ---: | --- |
| `m(int):void` | `method640(int)` | **76/76** | `754eca1686ff2ad99b1da0fadf82bf5f117ba88e25136bd7911d8ff1a280b1dd` |
| `k():void` | `method1241()` | **43/43** | `a91a1399ed71d332f6c0952ba3c6c92ffc8d65122c9c777f18e28211546c70ce` |
| **R213 total** | | **119/119** | Both actual donor method sources unchanged |
| **Cumulative R212 + R213** | Original h(), i(), j(), m(int), k() | **210/210** | Five independently selected method bodies |

A real isolated `javap -p -c -v` comparison shows exact original-v309 branch offsets, selected Code method lengths and JVM symbolic instructions after explicit original-to-readable field/member aliases. R213 adds the Python per-JVM-instruction verifier, rejecting changes in method flags, stack/locals, original exception handlers, resolved constants, branch targets, and every unmapped field or call.

## Explicit source symbol mappings

Original v309 `rs/n/c/ap` parent static fields `bQ:int`, `e:boolean`, `f:List` correspond to `Class179.field3656`, `field3647`, `field3648`. Original `rs/Client.eT` corresponds to `Client.tabInterfaceIds`. Original parent methods `k()` and `j()` correspond to `method1241()` and `method236()`, and original `rs/f/a.d()` corresponds to `Configuration.saveSettings()`.

Original spell categories `rs/n/c/ap$a.a/b/c` map to readable `Class176.field3590/field3591/field3592`, with original class type descriptors mapped to `Class176`. Widget sprite state uses original `rs/n/e.H` and `E` mapping to `WidgetComponent.widgetTable` and `sprite`; original `rs/n/c/V.f/g` map to `Class170.field3533/field3534`, with sprite type mapped from `rs/l/F` to `rs/graphics/Sprite`. Java `List.contains/remove/add` calls are expected to stay unchanged. Every original referenced field/call in the selected Code must match precisely one of those declarations or be rejected.

## Strict acceptance boundary

The compiled research class includes the two unchanged real `Class179` Java method implementations, but its other required members are declaration-only: `method236()` is NO-OP solely for compilation, and **six additional fake source dependency owners** (Client, Configuration, Sprite, WidgetComponent, Class170, Class176) are fully isolated from the original Java tree. None is counted as recovered original Code. The research class does not compile original full `rs/n/c/ap`, does not retain original superclass binary identity, and does not execute game behavior.

The compiled enum alias class deliberately is not byte-identical to the original; the only methods audited as original are `m(int)` and `k()`. Selected source Code recovery is not equivalent to complete client runtime or classfile binary parity.

Dedicated Ubuntu/Windows hosted tests use invented unrelated Java9 class sources to verify strict opcode/control flow/field maps, rejecting changed predicates, toggles, collection operations, descriptors, wrong method names and incomplete source body extraction. No original proprietary binary or Java is uploaded to CI.

**Next:** cover the long `rs/n/c/ap.a(ap$c)` original method via verbatim `Class179.method2689(Class178)` (large original 500+ bytecode offset method). Then recover the `register()`, four widget construction methods, constructor and original initializer under one deobfuscated source namespace and accept exact original JVM Code equivalence. Whole v309 client JDK-only source compilation remains blocked; last common private tree count is **1,295 Java, 2,358 compiler errors**. No reduction claimed here.
