# R224 — complete original v309 gambling-widget JVM Code parity from REAL readable Class170.java

**Client-side source recovery, stacked on [R223 #1110](https://github.com/Trexzo/SpawnPK-Client/pull/1110).** This recovers original `rs/n/c/V.class` from the existing readable gambling widget `rs/interfaces/widgets/Class170.java`. Unlike R223, which compiled Class170 but did not independently certify its original semantics, R224 compares all its methods with the exact SHA-pinned original JVM class.

## Private input provenance

- Original v309 JAR SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.
- Original `rs/n/c/V.class`: 4,727 bytes, SHA256 `51c5f49ff23619c5417a248788b15f66da5f1db5760e09835aa7aae6d6245686`.
- R203 1,295-source experimental ZIP SHA256: `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`.
- Existing REAL readable `Class170.java`: 9,043 bytes, SHA256 `73a2f01084e9abd1c86c9d6cad95cb35ce58873f0f45a771b79c36e2bad54b42`.
- Compiler-normalized actual readable `Class170.java`: 9,005 bytes, SHA256 `33def70a97c84201b14b501b8785068703bb04431f1d622eb66d0a6d96cb2d93`.
- Rebuilt normalized readable `Class170.class`: 5,474 bytes, SHA256 `4dddfefb8f688118c2b433ff0afd9c3834018b337ec8a6c255ad0b33b3e01aeb`.
- Rebuilt complete `Class179.class` SHA256 remains **exactly** `b88820d9893b5a2d5b2ff05f5b88aa6d77dc5ee4a66f377db83758f1590c1c6e`.

## Two explicit source normalizations — no game behavior invented

The real decompiled `Class170.java` as-is emitted **958 JVM instructions**, four more than original `rs/n/c/V.class`'s 954. The precise reason: inside `method1306()`, two repeated array-index expressions reload `childY` and `var6` where original Java 9 used the compact `dup2` bytecode form. R224 uses only these two semantics-preserving Java source normalizations:

```java
// Decompiler's expanded form
var1.childY[var6] = var1.childY[var6] - 9;
var1.childY[var6] = var1.childY[var6] + 13;

// Equivalent compound assignments (original compiler shape)
var1.childY[var6] -= 9;
var1.childY[var6] += 13;
```

The operands, array object/index evaluation and resulting values are unchanged for this local expression; exact original class Code comparisons then independently enforce the compiler result. The unchanged 9,043-byte donor and the 9,005-byte normalized source are separately SHA-pinned. Do not present R224 as a *verbatim* readable-source method parity proof; the compiler-shape adjustments are explicit and reversible.

## Complete original JVM verification

Using a fresh JDK21 `javac --release 9 -g:none -proc:none -implicit:none` build, empty external and original classpath/sourcepath, with the **same 18-source R223 set** (10 real readable including normalized Class179 and Class170, **8 separate NONORIGINAL temporary helper declarations**), the build passes with 0 errors, emitting exactly 18 classfiles.

| Original `rs/n/c/V` method | Real readable `Class170` method | Original JVM instructions |
| --- | --- | ---: |
| Constructor `(rs/l/K[])` | `Class170(HitsplatFont[])` | **4/4** |
| `a():void` | `register()` | **5/5** |
| `h():void` | `method1306()` | **607/607** |
| `i():void` | `method268()` | **223/223** |
| `m(int):rs/n/e` | `method701(int):WidgetComponent` | **102/102** |
| `<clinit>()` | Existing static field initializers | **13/13** |
| **Total** | **6 methods** | **954/954** |

All JVM **instruction offsets, opcode kinds, branch targets, numeric/string literals and unrenamed operands match exactly**. The original-to-readable member/type changes form **50 consistent symbolic mappings** (per-method and global SHA-256 fingerprints), including original `rs/n/c/W` → `Class168`, `rs/n/c/X` → `Class169`, original `rs/q/a/a/a` → `Class260`, `rs/l/e/f` → HUD `Overlay`, and the `rs/n/e` → `WidgetComponent` fields. The Python private verifier also checks method access, Code length, max stack/locals, exception handlers and StackMapTable presence.

**Importantly, R224 pins source-built Class179.class to the SAME exact R221–R223 accepted SHA**, proving the new source edits do not silently modify the independently verified spellbook parent.

## What this does NOT establish

- The original-method semantics of Class168 / Class169 / Packet-handler / Overlay dependency classes; those require separate original-classfile audits.
- The eight fake supporting declaration owners are *compiler-only*, not recovered game logic and not production artifacts.
- No original code was executed, and the rebuilt `Class170.class` is *not* byte-identical to the obfuscated original `rs/n/c/V.class`: Java owner and member names are intentionally renamed.
- No original-source redistribution authorization or full-client graphical runtime validation is claimed.

**Separate compiler-frontier caveat:** The R203/R223 1,295-source Java9/JDK-only build remains unfinished, last comparable measurement 2,358 errors. A **different** [R211 private 1,275-source Java11 build, PR #1084](https://github.com/Trexzo/SpawnPK-Client/pull/1084), reports **zero compiler errors** using an original-version non-game dependency library. These are different source sets and classpath conditions; do not conflate the counts or claim that R224 alone compiled the entire client.

Next: verify original `rs/n/c/W` and `rs/n/c/X` source classes against actual `Class168` and `Class169`, and reconcile the independent R211 full-source build with the R203/R224 precise method-evidence branch before prioritizing further fake helpers.
