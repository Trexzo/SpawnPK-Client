# R171 — six independently recovered original-v309 Packet read methods

Scope is the original v309 **client**, not a server emulator. This work extends [R170 #1061](https://github.com/Trexzo/SpawnPK-Client/pull/1061) with three additional source-recovered Packet methods, using the exact original SHA-pinned client JAR and independently compiled Java9 source. The private source stays OFF public GitHub pending redistribution rights.

## Original method-by-method JVM proof

Original Packet owner `rs/x/e.class` SHA-256 **b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2**, original complete v309 client JAR SHA **ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38**.

| Original method | Interpretation | Independently matching original JVM instructions |
| --- | --- | ---: |
| `B():int` | signed big-endian 16-bit | 37/37 |
| `r():int` | big-endian signed 32-bit | 52/52 |
| `s():float` | original `r()` raw int bits to float | 4/4 |
| **`p():int`** | second original big-endian 32-bit reader | **52/52** |
| **`o():int`** | unsigned big-endian 16-bit reader | **28/28** |
| **`y():int`** | unsigned byte, postincrement cursor | **13/13** |
| **Selected partial Packet source total** | | **186/186** |

`p()` and `r()` have byte-for-byte equivalent **decoded JVM Code instructions**, including original 52 instruction offsets through 82; they are two separate original method identities and BOTH have now been separately implemented and checked as Java. `o()` increments the cursor by 2 and reads unsigned big-endian bytes. `y()` applies unsigned masking after the original cursor postincrement. Original `s()` invokes the source-recovered `r()` through its exact original JVM name and descriptor.

A single PRIVATE source-only Java9 build using **no original Packet/game/external classpath binary** reproduces the six original JVM method instruction sequences. The private Java was compiled with `javac --release 9 -g:none -proc:none`; an independent normalized `javap -p -s -c` comparison proves every offset, opcode and resolved field/method target among these six methods.

Private exact artifacts:
- One-class selected six-method Java ZIP SHA256 **a8958a42d900ef5932354d4b9b79b1f5fa398ab5c1f065766b6fd8ddc31efbdf**.
- Source file bytes SHA256 **7c6108bfe762be603beeaa87c888314f15ca9a3f8974d0a0d7b43e01c76161e7**.

The rebuilt partial source's independent runtime harness passed **100 assertions**, including all six method behaviors across signed/unsigned short boundaries, both original big-endian int reads, Float raw bits, unsigned byte masks and cursor advancement. This executes only the isolated reconstructed Java class, not the original client.

## GitHub verification and boundary

R171 adds an exact original/private SHA-pinned source verifier which first demands **R170's complete 93-instruction B/r/s verification** on the same inputs, then compiles the one class from source and requires six selected JVM Code blocks to match the original (186 total), including the original method identities, offsets/branches, stack/locals and exception handlers. `s()→r()` closure is retained. No original binary compiler dependency is allowed.

Ubuntu and Windows synthetic CI create an independently compiled original JVM Packet test class and a separately source-built candidate containing six matching method bodies but a deliberately different seventh method. Tests reject a modified unsigned 16-bit shift, changed unsigned byte masking, changed second 32-bit reader, wrong SHA or wrong method counts. Runtime tests verify byte order and cursor positions; R170 regressions rerun.

**Not complete:** The original `rs/x/e` class extends `rs/a` and has other fields, constructors, pool operations and many methods not yet reconstructed. This is **six selected original method bodies**, not a complete client Packet source or classfile ABI/StackMap/runtime proof. The partial Packet source remains outside the canonical private recovered-source/v309/src candidate, still **1,276 Java files**. The last same-JDK-only whole-client compile reports **2,339 errors**; it has not been rerun or improved by this partial Packet pass. The historical normalized binary capsule's 516-error count used a different setup and is not comparable. Real-client R171 private verifier CLI replay is a separate step from the completed independent javap and runtime checks.
