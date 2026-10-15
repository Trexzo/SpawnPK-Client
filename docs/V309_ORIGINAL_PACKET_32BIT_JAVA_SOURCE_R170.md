# R170 — independently recover original v309 Packet raw 32-bit reader `r()`

Client-only original-v309 Java-source reconstruction. Stacked on [R169 #1060](https://github.com/Trexzo/SpawnPK-Client/pull/1060); milestone #1004 remains open. No original JAR or private original-derived Java is committed to this public repository.

## Exact private original source/JVM evidence

Original `rs/x/e.class` SHA256 **b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2**, inside the exact v309 original JAR SHA256 **ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38**. Original methods recovered in one independently recompiled partial Java owner:

| Actual original method | Original/recompiled decoded JVM instructions | Original final offset |
| --- | ---: | ---: |
| `B():int` signed short | 37/37 | 58 |
| `r():int` unsigned-byte big-endian 4-byte signed 32-bit | **52/52** | **82** |
| `s():float` calling `r()` and `Float.intBitsToFloat` | 4/4 | 7 |
| **Three original Java method bodies** | **93/93** | |

The newly reconstructed `r()` does exactly one `h += 4` cursor advancement, then reads `(g[h-4]&255)<<24`, `(g[h-3]&255)<<16`, `(g[h-2]&255)<<8`, `g[h-1]&255`, with the original left-associative 32-bit integer additions. Its source form was independently compiled with **`javac --release 9 -proc:none -g:none`**, with no original client, Packet or external binary on the classpath. Full private `javap -p -s -c` comparison confirms each of `r`'s 52 original vs independently compiled JVM instruction offsets, opcodes and resolved field targets is identical. Original `p():int` independently has the **same** 52-opcode sequence, but is **NOT** automatically counted as a fourth recovered method; it is separately selected only after a real source body compilation/identity check.

All THREE `B/r/s` bodies independently compile together in an original-named partial Java source. The `s→r` invoke is now closed by an independently recovered actual implementation, replacing R169's former `return 0` **unverified compile-only stub**. Same SHA-pinned private source:
- Private three-method source ZIP SHA256: **d83f755f6aedfeba92424f5302323561ddec683323880cf80dd533ea31842f55**
- Private Java file text SHA256: **780d1fe6ba475cc1271b34160cf81d09c20ae980d44176059f122dca66b996ba**

## Bit-level runtime evidence (source-only)

An independently compiled Java runtime harness executes ONLY the rebuilt Java class (never original private client binaries), with 50 passing assertions across signed 16-bit boundary inputs, big-endian unsigned-byte 32-bit patterns, sign-bit boundaries, negative zero, Infinity, a quiet NaN payload and float raw-bit identity. Cursor increments verified: +2 for signed short and +4 for each raw int or float read. This establishes relevant partial source behavior, **not** full Packet semantics.

## New GitHub proof and tests

R170 adds an exact SHA-pinned private verifier that *re-runs R169's* B/s acceptance against the same inputs, then compiles the one Packet Java owner under an **empty original/external project classpath** and compares **all three** original/recompiled JVM method Code blocks, including their exact class/member references, stack/locals, branch offsets and handlers. It also verifies original and rebuilt `s→r` self-call closure and `r`'s exact original 52-opcode length. The verifier checks pinned source and original-JAR SHA both before and after, and emits only sanitized aggregate information.

Cross-platform Ubuntu/Windows synthetic CI compiles a deliberately different non-SpawnPK Packet class, then recompiles its matching selected 16-bit/32-bit/float methods while leaving an unselected method with **different behavior**. A changed signed-short bitshift, altered most significant raw byte, changed float wrapper, bad SHA or expected count must fail. Separate compiled Java source-only runtime tests check signed-16, int, float raw-bits and cursor movement, and R169 regression reruns.

## Scope, completion and source distribution limits

The original Packet owner extends `rs/a` and has substantially more fields, methods, constructors, networking and pool dependencies. This private source contains **only selected B/r/s method bodies** and original `g:[B`, `h:int` signatures; it is **NOT** the complete original Java `rs/x/e` class and MUST NOT be installed into the canonical recovered-source/v309/src client tree. Original Packet superclass, Pool and other methods remain unresolved. Consequently the private canonical tree remains **1,276 Java files**, and the last independently measured JDK-only full source compiler frontier remains **2,339 errors**. The separate earlier normalized original-capsule 516-error frontier is not directly comparable. No full client compilation or runtime original equivalence can be claimed.

The private original-v309 JVM vs independent Java9 javap comparisons and source runtime assertions above have been executed. Hosted CI tests the reusable verification code on synthetic examples; **an exact new R170 GitHub CLI run against the real private JAR/source must be separately recorded before marking official R170 private replay acceptance**. Original Java source redistribution rights and external-binary provenance remain pending.
