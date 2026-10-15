# R176 — privately recovered original v309 Packet buffer and string methods

Client-side original-v309 Java reconstruction, stacked on R175 #1066. The SHA-pinned original Packet rs/x/e.class has twelve additional independently Java9-recompiled source method bodies.

| Original member | Function | Exact decoded JVM instructions |
| --- | --- | ---: |
| g():int | 24-bit big-endian read | 40 |
| E():long | two original D():int reads combined to 64 bits | 18 |
| w():String, F():String | zero- and newline-terminated strings | 28 + 29 |
| G():void, I():void | newline scan/skip methods | 17 + 17 |
| H():byte[] | newline-terminated byte array copy | 40 |
| a(byte[],int,int) | forward buffer writer | 23 |
| a(int,int,byte[]) | forward buffer reader | 23 |
| a(int,byte[],int) | reverse modified-byte writer | 28 |
| b(int,int,byte[]) | reverse buffer reader | 25 |
| b(byte[],int,int) | forward buffer reader | 23 |
| **R176 addition** | **12 methods** | **311/311** |

The combined PRIVATE original-named partial Java class now compiles with `javac --release 9` and no original client binary fallback; all **61 selected original JVM methods / 1,494 decoded JVM instructions** match, including offsets, resolved members, per-method access flags, stack depth and local slots. An independent original-JAR versus Java source rebuild comparison was actually executed locally, not just inferred from previous results.

SHA-256 verified original full v309 JAR: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Original Packet class: `b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2`. Private 61-method Java ZIP: `8636daaf6f60a7bb41c756ffa5eaa82e877c21d742ab60a2df515d6641068e38`. Private complete 61-method proof JSON: `40c9c5118e9f55aea2aa488b0423705109b1fa21096eabeeed6a5654e5bdb0dd`.

This is PRIVATE source evidence only, not official GitHub acceptance: the new R176 GitHub verifier and hosted CI have not passed yet. The original superclass rs/a, original constructors, networking, buffer pooling and other methods remain incomplete. In particular, do not install this partial Packet implementation into canonical recovered-source/v309/src; it remains 1,276 Java files. Whole-client javac last reported 2,339 JDK-only errors, not rerun for R176. No source redistribution permission is asserted.