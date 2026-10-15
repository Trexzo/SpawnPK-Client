# R178 — original v309 Packet Java constructors and twelve additional methods

Client-side reconstruction, stacked on R177 #1068; see source milestone #1004. Original client and all source-derived Java remain private.

## Independent private original JVM/source proof

A private Java 9 source build combines the complete original-derived `rs/t` and `rs/a` inheritance chain with the partial `rs/x/e` Packet class. The reconstructed Packet is no longer compiled against an invented Object superclass. Exactly one `rs/q/a` Java-only type *signature* is used during compilation; its method implementations remain unverified.

| New original method | Purpose | Matching JVM instructions |
| --- | --- | ---: |
| `<init>()` | inherited node constructor | 3/3 |
| `<init>(byte[])` | buffer-backed Packet constructor | 9/9 |
| `b(byte[])` | reset buffer, counters and attachment field | 16/16 |
| `a(byte[]):byte[]` | sequential byte-array copy | 23/23 |
| `a(String)` | string bytes and newline terminator | 29/29 |
| `e():int`, `d():int` | variable-length signed integer readers | 19/19, 19/19 |
| `f():int`, `v():int` | length-extended integer readers | 19/19, 16/16 |
| `A():int` | guarded two-byte read and fallback | 32/32 |
| `L():int`, `n():int` | guarded compact integer readers | 24/24, 24/24 |
| **12 newly restored** | | **233/233** |

All 61 original R176 method bodies retain their 1,494/1,494 instruction match after the superclass change. The combined original-named private Packet Java source now matches **73 distinct original method identities, 1,727 JVM instructions**, including exact original per-method access flags, instruction offsets, resolved field/method operands, stack limits, local and argument slots. The actual original Packet contains **80 non-static-initializer method bodies**, leaving **seven original methods and the class initializer** outstanding.

Private original-v309 JAR SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Original rs/x/e class SHA256: `b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2`.

Private 73-method Packet Java source ZIP SHA256: `e1eedb49cdfbc36a2719d129d720fc852e89f902a815d7d6ec87edee20af6a26`; private original-vs-recompiled proof JSON SHA256: `beb2c55b184c90c84bf08afd741f212095d67bb5d00554bf396d9f480755cead`. The separate compiler-only rs/q/a source-signature ZIP SHA256 is `6aef1198cfcc590b2d4a572452e8237558373ae14bb8e2601409363ab7c89b19`, intentionally **not an original-method implementation**.

## GitHub verification

R178 introduces a bounded original/Java source verifier using an exact SHA-pinned original JAR, exact private Packet Java candidate, **independently verified original Java Packet parents from R177** and exactly one compiler-only external type signature. It recompiles Java9 with no original game/class binary fallback, validates the original Packet superclass identity, excludes the seven explicitly unrecovered ordinary methods and static initializer, and requires 73 original method identities with all 1,727 original JVM Code instructions exactly matching. It does not publish any original source or JAR.

Cross-platform Ubuntu and Windows synthetic tests compile an entirely different example of two original-style parent classes and a derived partial class with original constructors, a deliberately missing original method and static initializer, and a Java-only auxiliary type. Tests reject changed Java body, wrong SHA pins and unexpected selected-method counts. R177 regressions rerun.

## Hard completion boundary

The remaining methods are `M():void`, `a(int):void`, `a(long):void`, `c():rs/x/e`, `c(int):int`, `g(int):void`, `k(int):int`, plus `<clinit>`. They use Packet pooling, external helpers, RSA and custom protocol operations and require separate original-evidenced Java work.

The incomplete Packet source is **not** added to the canonical private v309 recovered-source tree, currently at **1,278 Java files** after R177. Last controlled JDK-only full-client compiler frontier is **2,339 errors** and has **not** been rerun since this partial Packet recovery. This is neither a full original-client source compile nor permission to distribute original-derived Java. The independent private original/rebuilt JVM comparison is complete; exact GitHub R178 private CLI replay remains a separately tracked acceptance item.
