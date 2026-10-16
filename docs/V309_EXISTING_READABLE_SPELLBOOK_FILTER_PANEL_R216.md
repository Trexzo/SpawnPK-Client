# R216 — Existing readable Class179 filter-panel Java fully reproduces original v309 l() JVM Code

Client-side original-source restoration, stacked on [R215 #1102](https://github.com/Trexzo/SpawnPK-Client/pull/1102).

The exact SHA-pinned original client JAR (`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`) contains original `rs/n/c/ap.l():void`. The exact original `rs/n/c/ap.class` SHA is `b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4`.

The SHA-pinned existing private readable source `rs/interfaces/widgets/Class179.java` (SHA `8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2`) comes from the pinned R203 1295-Java tree (SHA `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`).

**Exact existing method source:** `Class179.method1592():void`, verbatim Java body SHA256:

`a15930f11270b2817890d51e00672a3a54d4e42697cb89cdd168bc767cf68114`

This method creates the spellbook filter UI, with one 12-child filter panel, four filter-option widgets, option text and their child coordinates. Its source is used **UNCHANGED**.

## Exact Java9 JVM evidence

Independent isolated JDK21 `javac --release 9 -g:none -proc:none -implicit:none` compile and `javap -p -c` comparison:

| Original source method | Existing readable method | Decoded JVM instructions | Last opcode offset | Code bytes |
| --- | --- | ---: | ---: | ---: |
| `rs/n/c/ap.l():void` | `Class179.method1592():void` | **160 / 160** | **314** | **315** |

Every original method JVM instruction has identical opcode, offset, integer/string constant and control-flow operand after precisely nine original→readable symbolic member/type renames. The readable generated class method's access/Code length/max-stack/max-locals/handler layout are separately verified by the R216 public private-input verifier. Nothing was executed.

The original source compiled as 160 instructions; the FIRST exploratory isolated build incorrectly gave **172 instructions** because the invented dependency declarations falsely returned `WidgetComponent` from various UI helper calls whose original descriptors return **void**. This caused 12 spurious `pop` operations. Correcting the NONORIGINAL compiler-only helper signatures to their original `void` return types made the unchanged readable method emit 160/160 matching original JVM instructions and offsets, without touching the real readable Java method body.

## Explicit resolved JVM member aliases

Nine different symbolic identities are used and all must be exercised:

- original `d(int):rs/n/e` ↔ `createPanelWidget(int):WidgetComponent`;
- `rs/n/e.k(int)` ↔ `WidgetComponent.allocateChildren(int)`;
- original static `a(int,String,String):void` ↔ `createDirectSpriteTextButton(...):void`;
- original widget font field `a:[Lrs/l/K;` ↔ `fonts:[Lrs/graphics/HitsplatFont;`;
- original overlay text creator ↔ `createOverlayTextOptionWidget(...):void`;
- original `h(int,String):void` ↔ `createFullScreenDirectSprite(...):void`;
- original `c(int,int,String):void` ↔ `createFullScreenSprite(...):void`;
- original option text creator ↔ `createOptionText(...):void`;
- original widget child coordinates `rs/n/e.b(int,int,int,int)` ↔ `WidgetComponent.setChild(...)`.

Unknown original JVM symbols, wrong argument descriptors, duplicate/missing method, changed source SHA, changed option numbers, changed opcode, added `pop`, altered coordinate, wrong member map and forged original-JAR fingerprint are rejected.

## Cumulative client-source progress

| Recovery PR | Original spellbook parent methods | Matching original JVM instructions |
| --- | --- | ---: |
| [R212 #1099](https://github.com/Trexzo/SpawnPK-Client/pull/1099) | `h,i,j` | 91 |
| [R213 #1100](https://github.com/Trexzo/SpawnPK-Client/pull/1100) | `m(int),k` | 119 |
| [R214 #1101](https://github.com/Trexzo/SpawnPK-Client/pull/1101) | `a(ap$c)` (3 explicit compiler-shape normalizations) | 243 |
| [R215 #1102](https://github.com/Trexzo/SpawnPK-Client/pull/1102) | constructor, `<clinit>` | 17 |
| **R216** | **`l`** filter panel, unchanged source | **160** |
| **Cumulative** | **9 of 14 original spellbook JVM methods** | **630** |

Independent [R210 #1097](https://github.com/Trexzo/SpawnPK-Client/pull/1097) already verifies the existing readable abstract `Widget.java` superclass (6 original JVM methods/11 instructions).

This stage DOES NOT claim all 14 spellbook methods, original runtime or compiled full v309 client; **five parent original method bodies remain**, including registration and substantial spellbook widget construction. No original-derived Java, client binary or assets are published in GitHub; only the fingerprinted verifier, unrelated synthetic fixture tests, CI and documentation are committed.

The last whole-client source-only compiler baseline remains **1,295 Java source files / 2,358 errors**. Do not claim an improvement in the full compiler frontier until merging a SHA-pinned and *actually compiling* source closure, not standalone research classes with compiler-only helpers. Original binary classfile identity, StackMap runtime verification, original-source redistribution rights and complete client compilation remain open. Keep R216 PR draft pending private official verifier replay and full acceptance.
