# R210 — validate actual existing deobfuscated Widget.java against original v309 JVM

Client-side original-source goal, stacked on [R209 PR #1096](https://github.com/Trexzo/SpawnPK-Client/pull/1096) and coordinated with R207 widget-base reconstruction. This is NOT a synthetic replacement source: the private verifier compiles **the exact pre-existing `rs/interfaces/widgets/Widget.java`** from the pinned R203 1,295-file recovered source tree. Only the two external dependency declarations are invented to make a class-local source-only Java9 compile possible, and they are expressly excluded from any original-recovery count.

## Real original evidence and readable-source evidence

- Original v309 full JAR SHA-256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.
- Original `rs/n/c.class` SHA-256: `65b1517e3630da9dcc79b8e53c28fa1622c000ff0825b33880ca3262d4d2b2a0`.
- Exact private recovered source-tree ZIP SHA-256: `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`.
- Existing donor `recovered-source/v309/src/rs/interfaces/widgets/Widget.java` SHA-256: `b3f77f45537ce65772e066f4bd27b9c3df99ca767479b5704927fb51df60985a` (530 bytes).

Local isolated compilation of the **actual donor source** succeeds under JDK21 `javac --release 9 -g:none -proc:none -implicit:none` with an empty external/source classpath and two separate, nonoriginal dependency declarations for `rs.interfaces.WidgetComponent` and `rs.graphics.HitsplatFont`. Direct `javap -p -c -s` disassembly against the original v309 class reproduces the same 6 original method bodies, 11 JVM operations and Code offsets, with every renamed superclass/field/member symbolic reference supported by this explicitly enumerated map:

| Original v309 name | Existing readable Java name |
| --- | --- |
| `rs/n/c` | `rs/interfaces/widgets/Widget` |
| original superclass `rs/n/e` | `rs/interfaces/WidgetComponent` |
| array element `rs/l/K` | `rs/graphics/HitsplatFont` |
| protected `a:[Lrs/l/K;` | `fonts:[Lrs/graphics/HitsplatFont;` |
| protected `b:Z` | `field3371:Z` |
| `<init>([Lrs/l/K;)V` | `<init>([Lrs/graphics/HitsplatFont;)V` |
| abstract `a():V` | abstract `register():V` |
| `a(int,String):V` | `onMenuAction(int,String):V` |
| `a(int):V` | `onOptionClick(int):V` |
| `b():V` | `close():V` |
| `c():Z` | `isEnabled():Z` |

The public R210 verifier performs explicit constant-pool-symbolic opcode normalization under precisely that mapping, requires the same original/candidate class flags and Java9 version, declaration inventory, method flags, Code length, bytecode offsets, stack/local limits, handler tables and all **11/11 operations**. It refuses unmapped field or method symbols, descriptor drift, changed method semantics, or different superclass linkage. It DOES NOT assume an arbitrary decompiler's source is original: the fixed source SHA, original JAR/class SHA and exhaustive member/Code proof are all mandatory in private mode.

## Remaining namespace and binary limitations

This result is **semantic source crosswalk**, not identical original classfile binary. The emitted readable Java name is `rs.interfaces.widgets.Widget`, not original JVM binary `rs.n.c`, and the superclass/field/method identities change under the explicit mapping. The original class and package share a name (`rs/n/c.class`, `rs/n/c/ap.class`); R209 already proves Java9 cannot compile their original names together, so a source-wide legal namespace map is required. This independent R210 proof establishes that the **existing readable Widget source is itself a viable original-semantic source**, not that the full client or the spellbook-filter parent compiles.

The R208 research branch currently has no commits relative to R207; R210 therefore stacks on R209 and preserves the existing R125 namespace authority, without assuming an undocumented R208 rewrite. Do not merge aliases across the tree without a single full-source namespace plan and original method/field references.

## CI, evidence boundary and next work

Dedicated GitHub Actions Ubuntu/Windows tests use **invented, unrelated** original-vs-readable Java9 widget sources. They exercise a good original-to-readable six-method 11-operation map, then reject changed enabled boolean, protected/private field flags, changed constructor store, missing/renamed abstract and concrete methods, wrong superclass, wrong mapped descriptors and mismatched SHA. No proprietary source, original binary or game code enters hosted CI.

Next implement the equivalent **full original-to-readable crosswalk for the spellbook parent** `rs/n/c/ap` against the existing 34,978-byte `Class179.java` donor. R205–R206 already prove 5 selected original methods; extend this to the 14 original method inventory with explicit subclass mapping, without assuming all inherited or obfuscated methods map automatically. The actual Class179 source has large dependencies, so any compiler-only support declarations must be inventoried and excluded from source-recovery counts.

Original-game runtime, nested class attributes, optional Code attributes, cross-version source compatibility, full private-input official R210 verifier replay, entire original-client compilation and source redistribution rights remain separate acceptance gates. **The last comparable R203 whole-client JDK-only frontier remains 1,295 source files / 2,358 errors.** No new whole-client diagnostic reduction is asserted.
