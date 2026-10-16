# R212 — Original v309 spellbook h()/i()/j() recovered FROM EXISTING readable Class179.java

Stacked on [R211 #1098](https://github.com/Trexzo/SpawnPK-Client/pull/1098), after [R210 #1097](https://github.com/Trexzo/SpawnPK-Client/pull/1097). This is **actual original JVM method-Code parity from real existing deobfuscated Java**, not a synthetic reimplementation.

## Exact original and donor evidence

Original v309 JAR SHA256:
`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

Original `rs/n/c/ap.class` SHA256:
`b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4`.

Existing private v309 decompiled Java tree ZIP SHA256:
`cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`.

Existing genuine `rs/interfaces/widgets/Class179.java` SHA256:
`8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2`.

The R212 private verifier extracts **verbatim Java method bodies** for three donor methods, requiring both complete donor-source SHA and each separate method-body SHA, without editing the Java implementations:

| Original method | Existing readable source method | Original JVM instructions | Pinned private donor method SHA256 |
| --- | --- | ---: | --- |
| `h():void` | `method1966()` | **10/10** | `3dfd9ee3a6df082885818958cba7eeaa4844061a7ae736fe8370c9ca8b2c5219` |
| `i():void` | `method3153()` | **62/62** | `a1c398fa3ed9b467d7303f81595425658574dc97288102ecb9fd536c04459ad6` |
| `j():void` | `method236()` | **19/19** | `b6f0954b935b9f6de4f774de664fc5fc399e18c38a7eac49a92af19dde47165d` |
| **Selected method-Code total** | | **91/91** | All 3 donor method bodies unchanged |

A local `javac --release 9 -g:none -proc:none -implicit:none` build of precisely those real three unchanged Java methods, with separately declared compiler-only support signatures for `rs.Configuration`, `rs.interfaces.WidgetComponent`, and `Class178`, successfully emitted the candidate JVM methods under the **readable** Java owner. Independent original-vs-built `javap -p -c` comparison shows original branch targets and byte offsets agree, with the original-to-readable symbolic aliases documented below.

**Typed JVM symbolic alias boundary**:
- original `rs/n/c/ap.d:Z` → readable `Class179.field3646:Z`;
- `g:[I`/`bI:[I` → `Class179.field3643:[I`/`field3644:[I`;
- original `rs/n/e.H` → readable `WidgetComponent.widgetTable`;
- original `rs/n/e.am`/`bc` → readable `WidgetComponent.childX`/`childY`;
- `rs/n/c/ap.i()`/`j()` → `Class179.method3153()`/`method236()`;
- `rs/f/a.d()` → `Configuration.saveSettings()`;
- original `rs/n/c/ap$c.values()` → readable `Class178.values()`;
- original `rs/n/c/ap.a(ap$c)` → `Class179.method2689(Class178)`;
- unchanged JDK call `java/util/Arrays.copyOf([II)[I`.

The public verifier independently compares **each entire method's decoded JVM Code**: exact instruction offsets, branches, symbolic owner/member/descriptor references after ONLY the listed aliases, opcode count, method access flags, max stack/local limits, exception table, and StackMapTable presence. Unsupported extra original symbolic references are rejected; a changed source body cannot be accepted from matching instruction count alone.

## Narrow scope and blockers

Only three real `Class179.java` method bodies are compiled. Its remaining Java members are **not** compiled into that research class: `method2689(Class178)` is a declared no-op signature for the selected method `j()`, not a claim that original long `a(ap$c)` body has been recovered. Other three support classes are invented compiler-only declarations, not original-sourced implementations. The temporary reduced class does **not** reproduce the original full 14-member class, its real `extends Widget` or runtime operations.

R205/R206 had already independently reproduced selected original method Code. R212 adds a critical new proof: **their h/i/j implementation is already present in the readable, deobfuscated client source tree and need not be reimplemented as duplicate original-name Java source**. That distinction is fundamental to eventually compiling a single fully deobfuscated source tree.

The existing R210 widget-base source parity and R211 exhaustive 14-field/14-method candidate map remain independent. Next repeat R212 for `m(int)` → `method640(int)` and `k()` → `method1241()`, then tackle `a(ap$c)` → long `method2689(Class178)` and the original class constructor/static initializer. Source-wide collision-free mapping and a full owner build still remain necessary.

Dedicated hosted Ubuntu and Windows tests use invented Java9 example classes and reject modified branch conditions, array-copy lengths, changed call order, missing JVM members, and invalid aliases. No original-derived Java/JAR is committed to public CI, original methods aren't executed, no full-original binary identity, class-level StackMap acceptance, source redistribution rights or full v309 client compilation are claimed. Last shared private source-only javac frontier remains **1,295 Java / 2,358 errors**, unchanged by this research-only stage.
