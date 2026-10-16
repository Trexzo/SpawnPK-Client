# R215 — existing readable spellbook Java constructor + static initializer reproduce original v309 JVM Code

Stacked on [R214 PR #1101](https://github.com/Trexzo/SpawnPK-Client/pull/1101). This is source-based original-client recovery using the PREEXISTING readable donor `rs/interfaces/widgets/Class179.java`; no invented class behavior is counted.

## Actual independently pinned evidence

- Original v309 full client JAR SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.
- Original `rs/n/c/ap.class` SHA256: `b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4`.
- Private R203 1,295-source decompiled tree SHA256: `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`.
- Existing readable `Class179.java` SHA256: `8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2`.
- Exact original-readable constructor source `Class179(HitsplatFont[] var1)` SHA256: `b7ad88602f8d1608ae741e31564fecd55f63988858e9935975ee5551e61a5852`.

This source already contains the real `Class179(HitsplatFont[])` call `super(var1)` and exactly five ordered Java static field initializers. A private temporary source compiler extracts the constructor verbatim and those five Java declarations verbatim, then compiles only these elements with a clearly nonoriginal compiler-only `Widget` superclass, `HitsplatFont` type and `Class176` enum for generics. It does NOT invent original parent Java logic.

## Bytecode comparison

Independent Java 9 `javac --release 9 -g:none -proc:none -implicit:none` with empty original/external binary and source classpaths emits an isolated readable `Class179.class`. Original-vs-candidate independent `javap -p -c` comparison shows:

| Original JVM method | Readable Java method | JVM operations | Last byte offset | Code bytes |
| --- | --- | ---: | ---: | ---: |
| `rs/n/c/ap.<init>([Lrs/l/K;)V` | `Class179.<init>([Lrs/graphics/HitsplatFont;)V` | **4/4** | 5 | 6 |
| `rs/n/c/ap.<clinit>()V` | Five ordered actual `Class179` field initializers | **13/13** | 26 | 27 |
| **R215 total** | | **17/17** | | |

The original superclass constructor `rs/n/c.<init>(HitsplatFont[])` is mapped explicitly to the independently validated readable `Widget.<init>(HitsplatFont[])` method name and type descriptor. The original static assignments map precisely to source field names:

- `c:int = 0` → `field3645 = 0`.
- `d:boolean = true` → `field3646 = true`.
- `e:boolean = true` → `field3647 = true`.
- `f:List = new ArrayList()` → `field3648 = new ArrayList()`.
- `bQ:int = -1` → `field3656 = -1`.

All original JVM instruction opcodes, offsets, constant-pool symbolic references under these SIX explicitly named aliases, method access, Code length, stack/local limits and exception tables match for these two methods. The readable compiled class's name and superclass binary name are not equal to the original: this is SOURCE SEMANTIC PARITY, not original classfile bit identity. Class-level optional metadata and JVM-verifier/runtime behavior are not accepted here.

## Cumulative source-evidenced progress

| Stage | Original spellbook methods recovered from existing readable Java | JVM instructions |
| --- | --- | ---: |
| R212 | `h(),i(),j()` | 91 |
| R213 | `m(int),k()` | 119 |
| R214 | `a(ap$c)` long spell filter, with three compiler-shape normalizations documented separately | 243 |
| R215 | **`<init>,<clinit>`** unchanged actual constructor/field initializers | **17** |
| **Cumulative original spellbook parent** | **8 of 14 JVM methods** | **470 matched original JVM instructions** |

R210 also verifies the separate readable widget superclass `Widget.java`, **6 of 6 original methods / 11 instructions**. There are still six unverified spellbook parent method bodies, including the UI registration path and widget-construction methods (large source areas).

The R215 public verifier enforces original JAR/class/source and constructor SHA, exact five initializer values and order, source-only Java9 compilation, emitted-class count, and original-vs-rebuilt full selected Code comparison. Unrelated invented hosted source tests reject changed flags/defaults, reordered initializers, wrong superclass signature and duplicate/missing constructors; no original Java/JAR is uploaded.

## Complete-client acceptance is still OPEN

Neither R214 nor R215 adds an original-named Java duplicate or fake dependency implementation to the private whole-client source tree. Existing sources are retained. The last comparable experimental source-only build remains **1,295 Java files / 2,358 Javac errors**. Whole-client compilation, source-wide R125 legal class/package mapping, runtime client compatibility, optional Code/Classfile metadata, full R215 original-private-input verifier replay and redistribution rights are not asserted. Keep PR DRAFT.
