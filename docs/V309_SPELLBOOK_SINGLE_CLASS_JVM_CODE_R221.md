# R221 — FIRST single-source / single-class original v309 spellbook method-Code proof

This is a distinct milestone from R212–R219's 14 **individually** compiled method bodies and R220's cross-batch evidence preflight. Here an independently preserved local proof compiled the **complete original-decompiled readable Class179.java as ONE Java 9 class**, then compared all its Code methods against the pinned original `rs/n/c/ap.class`. It is still **not** a whole-client source build.

## Actual private single-class replay

- Original full v309 JAR SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.
- Original `rs/n/c/ap.class` SHA256: `b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4`.
- Original-decompiled source tree ZIP SHA256: `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`.
- The actual donor `rs/interfaces/widgets/Class179.java` SHA256: `8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2`.
- Complete **source-normalized** readable `Class179.java` SHA256: `e274c0f12c36baeaa129920d5e259897a292b65a1138fc386f1413f00ff60406`.
- Resulting single Java9 `rs/interfaces/widgets/Class179.class` SHA256: `b88820d9893b5a2d5b2ff05f5b88aa6d77dc5ee4a66f377db83758f1590c1c6e` (17,543 bytes).

The whole `Class179.java` donor is identical to the existing readable Java **except exactly the three documented R214 long-filter compiler-shape transformations and the two documented R217 ancient-layout compiler-shape transformations**. The local complete-class source-only Java9 build used `javac --release 9 -g:none -proc:none -implicit:none`, empty original/external classpaths and **11 separately inventoried temporary NONORIGINAL compiler-only dependency declaration classes**. No original client binary was available to the Java compiler and no game code was executed.

**Results:** one emitted Class179.class with **14/14 original JVM methods and 4,314/4,314 decoded JVM instructions semantically matching** after enumerating permitted symbolic owner/field/method renames and exactly **178 Java constant pool `ldc`→`ldc_w` encodings**. These widenings change later raw offsets in 6 methods, but every original and candidate branch resolves to the same *instruction index*; operands and values remain equal. All distinct original-to-readable member aliases were SHA-pinned per method, **125 distinct per-method alias entries in aggregate** (entries counted across methods, so do not interpret as 125 globally distinct members).

Private original-input verifier replay: **PASS**. Complete method Code provenance report SHA256 `41094280841ebc3ae4cf634c0b0187fcfca793b224c9e9273b32892fbe0fde75`.

## Public GitHub verifier and negative testing

R221 publishes only a strict fingerprinted private-input classfile comparison, source/class hash pins, 14 method instruction and alias SHA contracts, and unrelated synthetic regression tests. The verifier disassembles the exact source-built Class179.class and original SHA-verified client JAR; it checks all 14 original instruction streams and requires *only* `ldc`→`ldc_w` substitutions, exactly 178 total; for branches it requires equivalent *target instruction indices*, and all renamed member/owner operand sets must match the SHA-pinned per-method alias maps.

Dedicated Ubuntu/Windows CI exercises a wholly invented 14-method/4314-instruction workload and deliberately corrupts opcodes, literal constants, method identity, aliases and original-input paths. **The original Java/JAR is not present in public GitHub Actions**, so hosted synthetic green is not itself an original private binary replay.

## What is still missing

- The 11 temporary dependency declarations in the isolated compiler experiment are **not accepted recovered original source**. Full real source dependency closure and actual full-client Javac are still blocked.
- The rebuilt class's Java owner, method/field naming and some JVM constant pool indices differ by design from the original obfuscated classfile. **Classfile byte-for-byte identity is not claimed.**
- Whole-client original v309 source-only Javac is still not successful; last comparable JDK-only private frontier remains 1,295 Java / 2,358 errors.
- Original-client runtime, resource/UI interactions, JVM verification outside source/class syntax, binary distribution rights and complete parity under genuine dependency implementations are not accepted.

**Next engineering target:** replace the 11 temporary stub declarations with independently recovered REAL readable dependent owner Java, compile these together with actual `Widget.java`, verify against original class-level JVM Code and whole-client compiler diagnostics; do not count temporary stubs as restored classes.

Stack: [R219 #1106](https://github.com/Trexzo/SpawnPK-Client/pull/1106) → [R220 #1107](https://github.com/Trexzo/SpawnPK-Client/pull/1107) → R221.
