# R175 — original v309 Packet signed and variable-length source readers

Original client-only Java recovery, stacked on R174 PR #1065. Six additional original Packet read-method bodies have independently compiled with Java9 and reproduce all selected original JVM Code instructions:

| Original member | Function | Original JVM instruction count |
|---|---|---:|
| l():int | big-endian unsigned short | 28 |
| m():int | big-endian signed int | 52 |
| q():int | special signed short threshold 60000 | 37 |
| u():int | signed big-endian 16-bit | 37 |
| x():int | second special signed short variant | 37 |
| t():int | variable-length int based on first byte; calls original y/o | 21 |
| **Additional R175** | | **212/212** |

The one-class PRIVATE original-named Java source now has **49 selected method implementations with 1,183/1,183 exact original JVM instruction offsets/opcodes/resolved field and method targets**. Independent private `javac --release 9 -proc:none -g:none` followed by `javap -v` comparison confirms original access flags, per-method max stack, local slots and arg counts across the 49 selected implementations. Its only original same-owner selected source calls comprise s()→r() and t()→y()/o(), all three directly source-backed.

SHA-pinned original v309 client JAR: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Original rs/x/e.class: `b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2`. Exact private R175 source ZIP SHA-256: `ee92ddb3b0368ff124a722cd33aeb049e156e21045a9c3a2ef336c6cc5edbc80`. Exact private R175 proof JSON SHA-256: `e99e25be5463d15f364b12b9777dd3002a54aa87827b4738a2bf7e09e4c30827`.

R175 public-source verifier re-runs R174's 43-method original/Java9 source-only proof against SAME private pins, then compares 49 selected original/recompiled JVM methods, 1,183 total instructions and all three same-owner call edges, without original/client/dependency binaries. Cross-platform CI uses independent synthetic method bodies and changed-expression/hash/count negative tests, plus R174 regressions. No original source/JAR/proprietary bytes uploaded to GitHub.

**Hard boundary:** 49 selected method bodies are not the whole original Packet class. Original superclass rs/a, constructors, pool/networking and remaining original methods unverified. Partial Packet remains outside canonical v309 recovered-source (1,276 Java files). Last JDK-only full-client javac count was 2,339 errors and is NOT rerun for this partial method evidence. Redistribution rights remain unresolved, and the new GitHub private verifier still requires a separate pinned-real-original run despite the independently completed private disassembly/compile proof.
