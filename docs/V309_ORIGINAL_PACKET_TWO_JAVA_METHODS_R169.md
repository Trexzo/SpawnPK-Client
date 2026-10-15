# R169 — exact original-v309 Packet signed-short and float wrapper Java methods

CLIENT original-source recovery; stacked on R168 #1059 and source milestone #1004. This stage does **not** claim a fully reconstructed original Packet class.

## New actual private original-JVM method recovery

Original JVM owner `rs/x/e.class`, full original class SHA256 `b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2`, from the pinned original v309 JAR SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

Two original Packet method bodies have been privately reconstructed as Java:
- **`B():int`, 37/37 original JVM instructions**, offset 0–58. It advances cursor `h` by two, extracts unsigned big-endian bytes from buffer `g`, and converts values above 32767 into their negative 16-bit signed representation by subtracting 65536. Original offsets, signed threshold, byte order, operand references and field declarations match isolated Java9 recompilation.
- **`s():float`, 4/4 original JVM instructions**, offsets 0–7. The original code invokes `r():int` and passes the returned bits to `java.lang.Float.intBitsToFloat(int)`. The `s` wrapper's method Code is recovered, **but r():int's actual source method body is NOT recovered in R169**. It is a compiler-only Java placeholder in this partial source.

The private isolated source class uses two original field declarations `byte[] g` and `int h`, two verified method implementations B and s, and an **UNVERIFIED r() placeholder** plus incomplete constructor and class hierarchy. It was compiled with `javac --release 9 -g:none -proc:none -implicit:none` and no original project or external binaries. It reproduces **41/41** original selected JVM instructions. A test harness executed only the source-rebuilt signed-short B() method (not the original game JAR), verifying 0, 32767, -32768, -1 and 4660 with cursor advancement in five cases.

Pinned private source:
- Partial Packet Java ZIP SHA256: `7715133b8cdb68b8f491d0027a11c213770193b125a07b8de73b23f28b2dc93c`.
- Partial Java source text SHA256: `93a648dc403db43599b49be338d48eff9ce77351ab0beb6418e5364a6f6748eb`.
- Original Packet class SHA256: `b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2`.

## GitHub verification and nonacceptance

R169 adds a separate SHA-pinned original rs-owned class method-level verifier, because R150/R162's matrix verification assumes a non-rs owner excluded for direct game dependencies. R169 reads the pinned original Packet .class, requires original byte[] buffer and int cursor identities, confirms exact JVM names/descriptors for signed-short B, float s and delegated int r, and compiles exactly ONE original-name private Java class with an empty original/external compiler classpath. It verifies only the TWO selected methods through the full R150 normalized resolved JVM Code inspector (opcodes, code length, branch targets, local stack limits and exception handlers), and verifies s has exactly one direct same-owner `r():int` call, explicitly **not selected or certified**.

A sanitized private report contains only selected count, instruction count, SHA pins and flags stating that r() remains unverified and the full original Packet class is not accepted. R169 intentionally **does not add the partial rs/x/e Java owner** to canonical `recovered-source/v309/src`, because it lacks the complete original superclass, Packet fields, constructors and other methods.

Hosted Ubuntu/Windows synthetic tests use a generic different rs-owned PacketBuffer class with modified method/member names, and prove that the signed-short and float methods match original JVM Code despite deliberately different unselected delegate implementation. Mutated signed-short shift, mutated float wrapper, bad SHA and accidental original Packet completion claim all fail or remain false. R168 five-math source regression runs too. Hosted CI never receives original SpawnPK JAR/source.

## Relationship to R168 and remaining work

The five original client math Java source classes `com/a/b/a/{a,b,c,d,e}` independently compile together from Java9 SOURCE and match **54 original methods / 4,656 original JVM instructions** with one compiler-only Packet class. R169 now proves the actual original `B` and `s` *methods* underlying those Packet signatures, but their original Packet-containing class is still **NOT** fully rebuilt. The direct original matrix→Packet call identities are now bytecode-grounded; prior decompiled-source aliases may still be ambiguous.

The PRIVATE canonical original v309 client candidate remains **1,276 Java files**, with a controlled JDK-only full javac count of **2,339 errors**, 52 fewer than the preliminary 1,271 source files. The 41 partial Packet method instructions do not change that error count because the unverified Packet skeleton is not canonicalized.

**Next:** independently recover original Packet `r():int` and relevant raw byte reads, extend exact-original method selection/closure, and work toward complete original Packet Java source from all its original methods. Then remeasure full-source javac with real original-evidenced Java rather than provisional stubs. Full client compilability, runtime parity and original-source publication rights remain outstanding.
