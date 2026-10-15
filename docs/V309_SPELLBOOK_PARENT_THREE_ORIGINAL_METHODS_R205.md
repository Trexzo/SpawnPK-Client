# R205 — first 3 exact original spellbook parent Java methods

Stacked on [R204 #1091](https://github.com/Trexzo/SpawnPK-Client/pull/1091); original v309 client-only source milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

## Actual original parent method recovery, NOT a complete class

The original v309 `rs/n/c/ap.class` is Java 9, SHA256 `b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4`, **14 original JVM methods** and 14 declared fields. An independently reconstructed original-named **PARTIAL Java9 `rs/n/c/ap.java`** source now contains three exactly verified method bodies:

| Original method | Original JVM instructions | Function |
| --- | ---: | --- |
| `h():void` | **10/10** | Toggle spellbook-filter state, trigger filter/placement refresh, save settings |
| `i():void` | **62/62** | Restore/reposition exact interface coordinates and `Arrays.copyOf` child arrays |
| `j():void` | **19/19** | Dispatch the three original spellbook modes through `a(ap$c)` |
| **Verified originals** | **91/91** | Original byte offsets, opcodes, operands, call/field symbols and stack/local limits all identical |

The pinned partial source file SHA256 is `0dd2d255a66d55f4022f74c601d6e78690a227c2139dd04ec73f8b6b8f5e8235`, exact private one-file source ZIP SHA256 **`74fef7ede24f9f704895c9a55d3ab44b0737b5e1267b010a55c4121bf3f07eea`**.

A local JDK21 `javac --release 9 -g:none -proc:none -implicit:none`, empty original/external binary/source classpaths, independently emits the partial parent `rs/n/c/ap.class`, the real R204 `rs/n/c/ap$c.class`, plus precisely three named **NONORIGINAL compiler-only** declaration classes `rs/n/c/c` (superclass), `rs/n/e` (widget fields), and `rs/f/a` (configuration API). Their separately SHA-pinned ZIP: `da2a513d6acae160ba440190651da6717a090ca62a981731ba45bb4e7971961d`. **No original game classfile is a compiler dependency.**

A local strict `javap -p -v` comparison against the SHA-pinned original JAR found exact equality across all 91 selected JVM instructions, byte offsets and symbolic operands (including branch offsets), method stack/local limits, and exception handlers. The selected source is real original-method Java recovery, not extracted original source or executable client acceptance.

## Important hard exclusions

The partial class also contains an empty `a(ap$c)` **compiler-only placeholder**, plus a nonoriginal generated default constructor; these are **NOT verified, original, or runnable game code**. Eleven original methods, the full 14-field declaration inventory, superclass source, widget source and most game subsystems are unrecovered in this parent. Do not count any placeholder as a reconstructed original method, and do not insert this partial Java in the original client recovered-source tree. Its purpose is proving original method source while keeping every other method explicitly unaccepted.

The current full-client experimental candidate is still **R204: 1,297 original-named Java files, 2,358 JDK-only compiler errors**. No reduction or full build claimed for the partial R205 parent.

## Public GitHub verification

This branch adds a strict private exact-input SHA-pinned isolated compilation verifier and unrelated synthetic Java9 source tests. The latter exercise three corresponding but **invented** methods, including branch/coordinate mutation, an altered enum dispatcher, original class SHA drift, wrong helper inventory and nonaccepted partial-method flags, on hosted Ubuntu and Windows. No proprietary client JAR or original-derived Java enters CI.

**Next:** original `a(ap$c)` is large and can be compared method-wise with decompiled `Class179.method2689`, followed by original instance filter dispatch and drawing methods. Recover original superclass/widget support sources independently, and only then admit the parent to a *private* whole-client source overlay. Other v309 client dependencies, JVM StackMap/classfile equivalence, real runtime and source redistribution rights remain unverified.


## Critical binary superclass namespace collision (2026-10-15 audit)

The original `rs/n/c/ap.class` has JVM superclass **`rs/n/c`** (binary Java class `rs.n.c`). The isolated Java9 partial-source compiler instead emits superclass **`rs/n/c/c`** from an intentionally NONORIGINAL test declaration. A Java package/class name collision prevents casually treating these as the same compiled owner. **Full class header identity is FALSE.** The public verifier now permits this *exact and only this* documented superclass difference for the SHA-pinned original owner; for unrelated synthetic owners it requires exact superclass equality. All three selected method JVM Code streams remain unchanged because they do not invoke that superclass. The original constructor is not among the accepted exact method bodies. Explicitly resolving/renaming this namespace collision is a prerequisite for complete original-parent source recovery and class ABI acceptance; never install `rs/n/c/c` as recovered original source.
