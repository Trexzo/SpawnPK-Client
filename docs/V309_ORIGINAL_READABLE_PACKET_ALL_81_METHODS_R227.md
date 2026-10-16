# R227 — FULL original v309 Packet JVM-Code recovery from existing readable Java

Stacked on [R226 #1113](https://github.com/Trexzo/SpawnPK-Client/pull/1113). This advances client deobfuscation from working socket-buffer Java to a complete original-code-verified source owner, independently comparable with R179's original-named Packet source. The donor is the **existing real readable** `rs/io/Packet.java`, not a guessed reimplementation.

## Independently pinned original and readable inputs

| Artifact | SHA-256 |
| --- | --- |
| Original whole v309 JAR | `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38` |
| Original `rs/x/e.class` Packet | `b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2` |
| Private 1,295-Java recovered-source ZIP | `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d` |
| Original-decompiled unmodified `rs/io/Packet.java` | `df4791701d6820b5ce41388be75d40364b2e8e20f08771d854e5fd62b9cf5030` |
| Private Java compiler-normalized `Packet.java` | **`16b77aa3c024bc93babc77213ab9ca825883a89478851c79a5c5d1a4c26ecc77`** |
| Complete single emitted `rs/io/Packet.class` | **`a47cc0aa2665fe2b8dfde80baeed5f3bc5db860bc7105cd97e0e0db2acc72597`** |

## Why the original unmodified readable Packet did not match immediately

The genuine readable Packet.java already had 81 correspondingly ordered methods but its initial source-only Java 9 build produced **2,289** decoded JVM instructions, versus **2,296** in original `rs/x/e.class`. Eleven original-versus-compiled method bodies contained differences. These did not justify copying original client code or introducing fabricated packet behavior: they were attributable to Java compiler source-expression choices and one inaccurate temporary configuration declaration.

Eight exact, deterministic source-rewrite *groups* affect **ten existing readable methods** without changing their decoded packet operations or logical outcomes:

1. `readBigSmart()`: temporary sum assignment before return rather than direct `return var1 + var2`.
2. `method38()`: equivalent explicit early return and fallback rather than conditional-expression return.
3. `method2073()`: original local-variable load/store instead of returning the field directly.
4. `readShortSmart()` and `method1571()`: equivalent explicit branching rather than the two shared conditional-expression returns.
5. `method1647()`: equivalent explicit branching for its other smart-number decoder.
6. `method1877()` and `method1569()`: `var1 = -65535 + var1` instead of `var1 += -65535`, preserving integer arithmetic but restoring the original `ldc` / `iload` / `iadd` order.
7. `writeString()`: compound increment `caret += length` rather than expanded assignment to restore original `dup` bytecode.
8. `encryptRsa()`: equivalent temporary `BigInteger var4 = var3` before `toByteArray()`, preserving data but restoring original local-variable instructions.

The **eleventh** mismatched method, static `newInstance()`, required **no Java source edit**: its existing `Configuration.field1313` declaration is really an `Integer`. The R226 temporary helper incorrectly declared it as primitive `int`, removing `Integer.intValue()` from the rebuilt Code. Correcting **only that compiler-only signature** to `Integer` reproduces the original JVM field-get/unbox sequence.

Each source edit is permitted only when the input has the exact SHA above, its original anchor count matches, and the entire final normalized source SHA matches. The owner-controlled original-decompiled Java file is never overwritten.

## Actual independent single-Packet-class acceptance

The normalized existing readable Packet source was compiled in the same 27-source JDK-only class graph as R226, with the six genuine R226 sources and the verified Class179/gambling callback ancestors. JDK 21:

`javac --release 9 -g:none -proc:none -implicit:none -classpath EMPTY -sourcepath EMPTY`

Result: **27 Java source files, 27 emitted classfiles, zero Javac errors.**

The resulting *single* Packet.class has all original 81 method Code bodies. Independent complete original `javap -p -c` and rebuilt `javap -p -c` comparisons found:

| Comparison | Verified result |
| --- | ---: |
| Original and rebuilt concrete JVM method Code bodies | **81 / 81** |
| Original decoded JVM instructions | **2,296 / 2,296** |
| JVM opcode differences | **0** |
| JVM byte-offset differences | **0** |
| Non-symbolic constant / branch / operand differences | **0** |
| Distinct consistent original-to-readable owner/field/method aliases | **30** |
| Global symbolic alias SHA256 | `d1b08d2f65323413b0bd330ed9b7c020b7c1aa131dd562bf398add6b012899d9` |
| SHA256 of all 81 mapped method headings, counts, per-method alias hashes | `bafb9dd66f4971c6dbe03eea27bf147e47bda63a6c9727a8a903ae43d0e303db` |

Original and rebuilt method `max_stack`, `max_locals` and Java9 Code length/exception-attribute layout are separately required by the R227 verifier. The original class has eleven fields and extends original binary `rs/a`; the readable class has eleven corresponding field candidates and extends readable `rs/DualNode`. The classes do not have byte-identical classfile names/constant pools and no binary identity is claimed.

All earlier accepted outputs remain unchanged:

- Full spellbook `Class179.class`: R221 accepted SHA `b88820d9893b5a2d5b2ff05f5b88aa6d77dc5ee4a66f377db83758f1590c1c6e` — 14 original methods/4,314 original-code instructions.
- Original gambling `Class170.class`, `Class168.class`, `Class169.class`: R224–R225 binary pins unchanged.
- Original packet callback superclass `Class260.class`: R226 accepted SHA `4032c94e90c9258a5094128e80c0648d8728128f8932a7b288f2b066e228b299`, 13 declarations/52 original Code instructions.

## GitHub CI and private-source boundary

The public R227 Python tool can replay the exact original JAR, R203 private source tree, and R221 evidence ZIP locally to reproduce every code-level comparison; it requires full artifact and source SHA guards. Its GitHub Actions tests use wholly **invented** 81-method/2,296-instruction fixtures and rejection cases for changing an opcode, numeric constant, byte offset, member alias, method identity, source rewrite anchor, or input SHA. Hosted tests never receive game Java or original client binaries.

The remaining 11 temporary dependency declaration classes are NOT considered recovered. No game code was executed, no server connection was established, original classfile byte identity is not claimed, and neither source-publication authorization nor a full source-compiled v309 client is asserted. The last comparable full-client JDK-only compiler frontier remains R203: 1,295 Java files and 2,358 compiler errors. A separate Java11 build candidate under other conditions is not evidence of the same frontier improving.

**Next engineering target:** replace the remaining fake GUI/HUD Overlay dependency with actual source, then reconcile the private fully verified readable Packet.java with the R179 original-named Packet recovery and with the other team's Java11 whole-source candidate. Keep PR DRAFT pending complete client source closure, runtime verification and rights.
