# R207 — exact original v309 abstract widget superclass Java source

Stacked on [R206 #1093](https://github.com/Trexzo/SpawnPK-Client/pull/1093), original source milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

## Complete class source, independently original-JVM verified

Original class `rs/n/c.class` (Java name `rs.n.c`) SHA256:
`65b1517e3630da9dcc79b8e53c28fa1622c000ff0825b33880ca3262d4d2b2a0`.

Original v309 client JAR SHA256:
`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

Private original-named `rs/n/c.java` source text SHA256:
`18191a5a99978627b49769d5031db1b003f146a7e6bbba2af256712359d4066b`.
Private one-Java-source ZIP SHA256:
**`2a69da84230573377795311331eb30196aff132f8bc55f18853d841bba57d148`**.

The original is an abstract widget superclass extending `rs/n/e`, with two protected fields: `a:rs/l/K[]` (font/UI elements) and `b:boolean`. The **entire original JVM inventory**, original names, descriptors, access flags, superclass, Java9 version and concrete JVM Code matches:

| JVM member | Original instructions | Meaning |
| --- | ---: | --- |
| `<init>(rs/l/K[])` | 6/6 | Original superclass invocation, stores font list |
| abstract `a():void` | No Code | Widget registration interface; exact original abstract access/descriptor |
| `a(int,String)` | 1/1 | Empty menu callback |
| `a(int)` | 1/1 | Empty option callback |
| `b()` | 1/1 | Empty close callback |
| `c():boolean` | 2/2 | Original default `true` enabled predicate |
| **Original concrete JVM Code** | **11/11** | Exact byte offsets, method descriptors, field and call operands |

The genuine original `rs/n/c.java` compiles independently with `javac --release 9 -g:none -proc:none -implicit:none` using two explicitly inventoried NONORIGINAL compiler-only declarations for its dependencies, `rs/n/e` and `rs/l/K`, ZIP SHA256 `c43928dad50b7dbfa828c6f0a7c2b7f17ecf4ce4abb8a4fb5781b4f287855dc0`. The original JAR is **only used as read-only binary evidence**, never on `javac`'s dependency classpath and never executed.

An independent comparison against the existing private recovered client source `rs/interfaces/widgets/Widget.java` finds a strong structural match: it extends decompiled `WidgetComponent`, contains the corresponding protected font array and boolean, and has register/menu/option/close/enabled methods with the same six-method shape. This is **mapping evidence**, not independent proof that all field/function names can be automatically replaced across the client.

## Critical legal Java namespace collision

The v309 original JVM binary uses both:
- class **`rs/n/c.class`**, Java name `rs.n.c` (this base class);
- classes under package **`rs.n.c`**, e.g. `rs/n/c/ap.class`.

JDK Java **source compilation cannot legally contain an `rs.n.c` class and an `rs.n.c` package simultaneously**. A direct combined source compilation generates `package rs.n.c clashes with class of same name`; this was reproduced locally. The earlier R205/R206 original-named partial `rs/n/c/ap.java` therefore used a deliberately NONORIGINAL `rs/n/c/c` fake superclass. Its five selected original method bodies matched exact Code, but **its compiled superclass binary name did not match original**. The earlier PRs were explicitly corrected to report that.

**The R207 base class is independently full-original-JVM verified but CANNOT be overlaid as original-named `rs/n/c.java` into the existing v309 private source tree while source children remain under `rs/n/c/*.java`.** A stable, source-wide semantic namespace mapping, e.g. deobfuscated `rs.interfaces.widgets.Widget` / child `rs.interfaces.widgets.Class179`, is required. Do not fake or overwrite class identities; do not claim a simultaneous original-named compilation.

## Compiler frontier and next

R207 does **not** alter the SHA-pinned R204 private experimental **1,297 Java file source tree** (SHA256 `5c971fcb3c2e29bd3623ba728f6e967f41a11eafad6adb2d91b91fa56a60fe5b`). The unchanged JDK-only controlled source compilation still reports **2,358 errors**; no reduction is claimed.

Public GitHub adds a SHA-pinned private original source recompile/bytecode+member ABI verifier, an unrelated synthetic Java9 abstract widget with changed method, superclass, abstract signature, fields, binary digest and dependency-owner negative tests, and hosted Ubuntu/Windows CI. No original-derived Java or game JAR is included in GitHub.

**Next:** formalize a collision-free original-to-deobf logical-ID mapping for `rs/n/c`, `rs/n/c/ap`, and their original parent dependencies. Recover the large spellbook parent method `a(ap$c)` and nine remaining parent method bodies using the original v309 JVM evidence, then test a private deobfuscated **one-Java-tree** build without inventoried fake source declarations. The complete client runtime, original superclass support dependencies, classfile attributes and licensing remain unverified. Keep PR DRAFT.
