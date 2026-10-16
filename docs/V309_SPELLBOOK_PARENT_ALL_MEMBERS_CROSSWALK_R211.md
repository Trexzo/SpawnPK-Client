# R211 — exhaustive original spellbook parent to existing Class179 source member crosswalk

Client-side v309 source recovery, following [R210 #1097](https://github.com/Trexzo/SpawnPK-Client/pull/1097). The purpose is to stop further duplicate or guessed Java reconstruction: the actual existing decompiled `rs/interfaces/widgets/Class179.java` appears to correspond to original `rs/n/c/ap`, and its **complete declaration-level candidate map** can be pinned and independently checked before method-by-method JVM Code reconstruction.

## Grounded inputs

| Evidence | SHA-256 |
| --- | --- |
| Original exact v309 client JAR | `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38` |
| Original `rs/n/c/ap.class` | `b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4` |
| Private 1,295-Java source ZIP | `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d` |
| Existing `Class179.java` donor (34,978 bytes) | `8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2` |

The original v309 binary has **14 declared fields and 14 JVM methods**. The decompiled readable Java declares 14 corresponding static fields, 13 explicit Java methods and ordered field initializers which generate the fourteenth JVM method, `<clinit>`. Its immediate superclass is `rs.interfaces.widgets.Widget`; original immediate superclass is `rs.n.c`, whose existing readable counterpart is independently verified by R210.

## Complete original-to-readable field candidate map

| Original JVM field | Existing Java field |
| --- | --- |
| `g:int[]` | `field3643:int[]` |
| `bI:int[]` | `field3644:int[]` |
| `c:int` | `field3645:int` |
| `d:boolean` | `field3646:boolean` |
| `e:boolean` | `field3647:boolean` |
| `f:List<ap$a>` | `field3648:List<Class176>` |
| `bJ`, `bK`, `bL`, `bM`, `bN`, `bO`, `bP` (Sprite-typed) | `field3649` through `field3655` |
| `bQ:int` | `field3656:int` |

Each original field's **binary descriptor** must agree with the matched donor's Java type and original field-order position. The matcher refuses any field count, type or ordering change. This is evidence for a mapping candidate; original memory behavior remains separately testable.

## All 14 original JVM method identities and source declaration candidates

| Original method | Decompiled Java candidate | Evidence status |
| --- | --- | --- |
| `h():void` | `method1966()` | R205/R206 independently reconstruct the original Code; source call-path anchors check toggle/save |
| `i():void` | `method3153()` | R205/R206 original Code recovered; widget 1151/12424 + `Arrays.copyOf` anchors |
| `j():void` | `method236()` | R205/R206 original Code recovered; Class178 iteration anchor |
| `a(ap$c):void` | `method2689(Class178)` | **Unverified full Code**, source-dependent candidate |
| `<init>(rs/l/K[]):void` | `Class179(HitsplatFont[])` | Original superclass name collision still requires legal mapping |
| `a():void` | `register()` | Full Code unverified |
| `m(int):void` | `method640(int)` | R206 original partial Code recovered, donor source anchors 41910/41913 |
| `k():void` | `method1241()` | R206 original partial Code recovered, category-button sprites anchors |
| `l():void` | `method1592()` | Full Code unverified |
| `m():void` | `method2352()` | Full Code unverified |
| `n():void` | `method3532()` | Full Code unverified |
| `o():void` | `method892()` | Full Code unverified |
| `p():void` | `method1712()` | Full Code unverified |
| `<clinit>():void` | existing field initializers | Original static initializer not JVM-verified against donor |

**Important distinction:** the checker validates 14/14 **declaration candidate mappings** using original classfile order/descriptor and SHA-pinned source order/type and distinctive callsite tokens. It does NOT certify 14/14 JVM method Code equality, stackmap equivalence, or full runtime behavior; those require rebuilding the source with a collision-free namespace and auditing every method's complete JVM operations.

## Next concrete code work

Use the verified R210 readable superclass and R209 collision-safe namespace rules to source-compile original-to-readable `Class179.java` against independently inventoried real dependencies or separately labelled compiler declarations, then compare original `rs/n/c/ap` method-by-method against the compiled existing donor, using the exact fixed member maps here. Prioritize `a(ap$c)`, `a()`, constructor and `<clinit>`; accept only original Code that matches. Avoid adding another original-named duplicate into the canonical Java tree.

Dedicated hosted Ubuntu and Windows tests deliberately use invented source shapes and reject lost/duplicated/reordered fields, a changed Class178 parameter, missing settings callbacks, omitted initializers and wrong SHA. The private real original-JAR+donor ZIP verifier must be replayed separately. No original Java/JAR is published, and the entire v309 client still does not compile. The most recently comparable source-only frontier remains **1,295 Java files and 2,358 compiler errors**.
