# R206 — five original v309 spellbook parent Java method bodies

Stacked on [R205 #1092](https://github.com/Trexzo/SpawnPK-Client/pull/1092), original source milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). No original-derived Java or client binaries are committed to GitHub.

## Source recovered against original pinned v309 bytecode

Original `rs/n/c/ap.class` SHA256: `b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4`.

Exact original v309 JAR SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

Private partial source Java file SHA256: `9009e18c99617ce5d0c8582c131cc26308a29ff12118462c7ac9527b22e8e47f`. Private original-named one-Java-file candidate ZIP SHA256: **`34a149d80c5c8b1b6f4614697a65c9f59618d444bd42f5661a1b9525669c0df7`**.

Five independently reconstructed method bodies:

| Original JVM method | Verified original decoded instructions | Function |
| --- | ---: | --- |
| `h():void` | 10/10 | Toggle spellbook filtering and persist settings |
| `i():void` | 62/62 | Real interface coordinate/array copy updates |
| `j():void` | 19/19 | Iterate modes and dispatch spellbook placement |
| `m(int):void` | 76/76 | Original spellbook filter button IDs 41900/41903/41910–41913 and category flags |
| `k():void` | 43/43 | Four original spellbook category filter icon references |
| **Total** | **210/210** | Exact JVM instruction offsets, opcodes, symbolic references, branches, stack/local limits |

Local compiled original-named Java with JDK21 `javac --release 9 -g:none -proc:none -implicit:none` and EMPTY original/external classpath/sourcepath. Two previously recovered **REAL** Java enums `rs/n/c/ap$a` and `rs/n/c/ap$c` compile alongside the partial parent. Six externally referenced source dependencies are **explicitly labeled NONORIGINAL compiler-only declarations**, separately pinned in ZIP SHA256 **`c75db592f6c9e5d8b734f226055314c7080ae90eb670eed7f871e60c98ace7ef`**: superclass `rs/n/c/c`, widget `rs/n/e`, `rs/f/a` configuration signature, `rs/n/c/V` icon holder, `rs/l/F` icon type, and `rs/Client` selected spellbook state. These invented helpers are neither accepted as original JVM source nor present in the full-client source overlay.

The pinned private `javap -p -v` replay of the original versus rebuilt partial parent confirms all **210 original instructions and their exact byte offsets, member symbols and branch destinations**. No actual game, network, GUI, configuration or MIDI code was executed. The selected method bodies are real original-derived Java recovery, not an executable complete parent.

## Hard nonacceptance

The original `rs/n/c/ap` has **14 JVM methods**; only **5 are independently recovered** here. In particular, the reconstructed partial class still contains an EMPTY `a(ap$c)` **NONORIGINAL compiler-only placeholder**, and its generated constructor and missing other members are NOT original. The source does not reproduce the original 14-field ABI. None of these are an accepted original class body, and the partial parent **MUST NOT be installed in canonical recovered-source/v309/src**.

The full experimental recovered-original Java source tree remains the **R204 1,297-file snapshot**, SHA256 `5c971fcb3c2e29bd3623ba728f6e967f41a11eafad6adb2d91b91fa56a60fe5b`. Identical JDK-only Javac still reports **2,358 compiler errors**. No R205/R206 partial parent or compiler-only support declaration has been added to the full tree, and no compiler improvement is claimed for either stage.

## Verification infrastructure and next

The public R206 Python verifier SHA-pins the original full client JAR/class, source ZIPs of the 2 real enums and partial parent, and exact six helper owner declarations. It recompiles JDK9 source-only, requires exactly 3 real and 6 fake emitted classfiles, and compares the 5 selected original methods via strict CP-resolved opcode/offset/member/branch verification. The returned report always rejects complete parent/field/runtime claims.

Hosted Ubuntu/Windows CI uses invented, unrelated Java9 source classes with 5 similarly shaped method identities; negative cases mutate button IDs, filter selections, icon branches, source digests and helper inventories. CI never receives original client binaries or original-derived source.

**Next:** the large `a(ap$c)` mode-filter dispatcher and its original client-side widget superclass dependencies; recover remaining instance methods and original constructor with one original source candidate, then validate all 14 methods, 14 fields and full source-only compilation together. The complete v309 client does not yet compile; source redistribution rights and runtime acceptance are unknown. Keep this PR draft.
