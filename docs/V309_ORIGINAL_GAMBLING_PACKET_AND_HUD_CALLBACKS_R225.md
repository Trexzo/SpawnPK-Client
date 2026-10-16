# R225 — original v309 gambling packet + HUD callback JVM Code from real readable Java

This batch continues [R224 #1111](https://github.com/Trexzo/SpawnPK-Client/pull/1111) and the actual 18-source Java9 dependency closure in [R223 #1110](https://github.com/Trexzo/SpawnPK-Client/pull/1110). It independently verifies the **original source semantics of the two gambling callbacks**, which R223 previously compiled but did not accept as original JVM method-Code matches.

## Exact original and decompiled source ownership

- Original v309 full JAR SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.
- Original `rs/n/c/W.class` → existing `rs/interfaces/widgets/Class168.java`. Original class SHA256 `a4dfe82736a05630859290ed16361af359b8bc0b45c9f3441d15b56fde105dbd`. Exact original-decompiled readable source SHA256 `28a814fd331abe90eb2711929d4edc84c184d7a41bc8fcf90b13117b5ec20103`.
- Original `rs/n/c/X.class` → existing `rs/interfaces/widgets/Class169.java`. Original class SHA256 `74e96c4c84103eb7f8fecdc06cec69077d85d87b38d5cc9f82696ec1cb9b4859`. Unmodified original-decompiled readable source SHA256 `591e74de23e0824070636a8ff4a5197e347e5b495f2fe2698b880f05b664d996`.
- R203 original-decompiled source tree SHA256 `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`.

The real Class168 Java source is compiled **unchanged**. Real Class169's only mismatch is a compiler-shape difference at the start of `method1640(Client,Class69)`: the decompiler nested all content under `if(var2 == Class69.field2525)`, whereas original Java compiled an equivalent `if(var2 != Class69.field2525) return;` early guard. R225 makes exactly that predicate inversion/early-return conversion and removes its now-unnecessary closing brace; no field, string, drawable, gameplay condition, timeout or call is otherwise changed. The normalized Class169.java SHA256 is **`285d42d5c59f442057c354635ef95ee05e2d32d1f01debae0c82b7e44c73bce8`**.

## Independent complete original JVM Code comparison

A clean original-v309 source-only `javac --release 9 -g:none -proc:none -implicit:none` build from the **same 18 source owners** as R223/R224, using empty original/external classpaths, produces exactly 18 classfiles and **zero javac errors**. The nine existing genuine dependency source owners remain actual decompiled Java, Class179 is the previously verified complete normalized original spellbook source, and eight separate compiler-only helper declarations are still explicitly NONORIGINAL.

| Original owner / original JVM method | Real readable Java method | Matching original JVM operations |
| --- | --- | ---: |
| `rs/n/c/W.<init>()V` | `Class168()` | 3 |
| `rs/n/c/W.a()V` | `Class168.handlePacket()` | 17 |
| **Original packet callback** | **2/2 methods** | **20/20** |
| `rs/n/c/X.<init>()V` | `Class169()` | 3 |
| `rs/n/c/X.b()V` | `Class169.method1484()` | 1 |
| `rs/n/c/X.a(Client)Z` | `Class169.method3175(Client)` | 9 |
| `rs/n/c/X.b(Client,OverlayMode)V` | `Class169.method1640(Client,Class69)` | 98 |
| `rs/n/c/X.c()V` | `Class169.method904()` | 1 |
| **Original HUD callback** | **5/5 methods** | **112/112** |
| **R225 total** | **7 original methods** | **132/132** |

For each method, the complete JVM opcode, **byte offset, branch target, string/numeric operands, original-to-readable symbolic member identities, Code length, method flags, stack/local limits, exception table and StackMapTable presence** are compared against the original binary. All pass. The original-to-readable symbolic maps contain four distinct aliases for packet callback W and 13 for overlay callback X; the per-method and aggregate SHA-256 fingerprints are committed to the verifier.

The rebuilt Class168.class SHA256 is `0604158afc9475bdae752a0e2df7fd64483b2208dd7c571f709239416779db02` (**no source edits**). The normalized Class169.class SHA256 is `cae4619b7ffc5c653f38c22277ae0b6a3c5309f962033aabb2a200da74c16592`.

**The source-built R224 Class170.class SHA `4dddfefb8f688118c2b433ff0afd9c3834018b337ec8a6c255ad0b33b3e01aeb` remains unchanged**: its original `rs/n/c/V` **6/6 methods / 954/954 JVM instructions** stay proven. The complete rebuilt Class179.class remains byte-for-byte identical to R221 SHA `b88820d9893b5a2d5b2ff05f5b88aa6d77dc5ee4a66f377db83758f1590c1c6e`, preserving all 14 methods / 4,314 original JVM operations.

Across R224–R225, the three real gambling widget/callback classes have **13 original method bodies and 1,086 matching original JVM operations**. These are separate from, and do not inflate, the 4,314-instruction spellbook parent result.

## Constraints and next work

The original gambling packet source `Class168` uses an abstract `rs/scriptpacket/Class260`, and overlay `Class169` uses `rs/graphics/hud/Overlay`, neither accepted as original semantic sources yet. They remain two of R223's eight temporary signature helpers. The tests neither launch nor execute original client behavior, and no private original-derived Java/JAR is uploaded to GitHub Actions; hosted synthetic positive/negative tests prove verifier and Java9 guard integrity only.

**Next:** audit and source-compile original original-classfile counterparts for actual readable `rs/scriptpacket/Class260.java` and `rs/graphics/hud/Overlay.java`, then selectively replace those compiler-only dependencies while retaining the exact accepted Class168/Class169/Class170/Class179 classfile SHA pins. Reconcile independently compiled R211 Java11 1,275-source branch [PR #1084](https://github.com/Trexzo/SpawnPK-Client/pull/1084) with this R203/R225 Java9 original-Code-evidence branch. Do not confuse their compiler diagnostics or claim the full client can be launched from this experimental 18-source closure.

The R203/R225 Java9 full-source frontier remains last *comparably* measured at 1,295 source files / 2,358 errors; PR #1084 documents a separate 1,275-source Java11 dependency-resolved full-build success. Runtime, original obfuscated classfile byte identity, original client-wide method parity and redistribution rights remain open. Keep R225 draft pending private exact-input replay, dedicated CI and complete parent dependency closure.
