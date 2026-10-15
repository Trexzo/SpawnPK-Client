# R167 — recover original v309 quaternion Java source and integrate five-class math lane

Client-only source recovery, stacked on R166 #1057 and original-source milestone #1004. All original user binary/source evidence stays private.

## New original quaternion source recovery

The original com/a/b/a/c.class is SHA256 `37ffe0bbc272b080bcede9b975f99f877da05375089b256c656566d8790c41df`, length 1,918 bytes. It declares **11 JVM methods** and seven fields (three static pool fields, four float components). The original-named Java9 source class was reconstructed privately, with original synchronized pool acquire/release and exception handlers, constructor/reset, four-float assignment, axis-angle sine/cosine, quaternion composition, equals, hashCode, toString and static initialization. Its independently rebuilt JVM instructions match **314/314** original decoded JVM instructions, including offsets and resolved field/method references and branch destinations. The original pool static initializer required leaving its count field uninitialized in the declaration and writing to it once in the initializer; duplicating the default assignment would alter the original instructions.

Source-only Java9 recompiled class length 1,913 bytes, SHA256 `35df74bf7383b918902556b6d7cc544110f29dd0c832822e5da3578b9d50bbfd` (NOT byte-identical to original). Private new quaternion Java source file SHA256: `fd5971f151e3f3220188a714f4236116d9fd097810598552db1af43d01a02580`.

## Private recovered-source tree and full JDK-only compiler measurement

Adding exactly this original source owner to the prior 1,275-file tree produces **1,276 Java files**; previous Java contents remain unchanged and no original Packet scaffolding is included.

- Original whole v309 JAR SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`
- Prior 1,275-file private source tree: `60e18b49e671545f993b326398cb6654f80cbd0ac36d2c2b07877ad056387e7f`
- New 1,276-file private source ZIP: `75a5c61695a6f09179b0cb80738e0e38402b5d74e428618a9ac01165bac6e501`

Controlled JDK21 javac --release 9 -proc:none -implicit:none -Xmaxerrs 10000 with every Java file listed and no original game/external binary classpath: original 1,271 Java **2,391 errors**, R163 matrix 1,272 **2,364**, R164 vector 1,273 **2,358**, R165 angle 1,274 **2,355**, R166 transform 1,275 **2,353**, now R167 quaternion 1,276 **2,339**. Net **52 fewer** reported JDK-only errors from original candidate. Still NOT a full client build. The historical 516 error frontier used a different provisional dependency binary classpath and cannot be compared directly.

## Joint original source-only math subsystem

Private javac --release 9 compiled original reconstructed **five classes at once**:
- com/a/b/a/a (transform): 8 methods, **401** matching instructions
- com/a/b/a/b (matrix): 24 methods, **3,780**
- com/a/b/a/c (quaternion): 11 methods, **314**
- com/a/b/a/d (angle helper): 6 methods, **81**
- com/a/b/a/e (vector): 5 methods, **80**

**54/54 original method bodies and 4,656/4,656 decoded original JVM instructions match in this ONE joint rebuild.** The six emitted classes are precisely the five original math owners plus a **separately supplied, compile-only original rs/x/e Packet Java signature stub** containing B():int and s():float. NO original v309 .class or external binary is used as the compiler dependency. The Packet stub's bodies are NOT original-evidenced runtime implementations and are NOT included in the canonical 1,276 Java source tree.

The five original source owners are fully evidenced as JVM Code, not fully byte-identical classfiles or a working client runtime. Full classfile metadata and complete Packet semantics still require distinct verification.

## New GitHub R167 verifier

R167 requires the original-JAR and original quaternion Java ZIP SHA pins, source-only Java9 recompilation, **all 11 method bodies and seven fields**, original opcode offsets/operands/Code and monitor exception handler parity, original class modifiers/supertype, and StringConcatFactory bootstrap recipe agreement. Synthetic Ubuntu/Windows fixtures implement a DIFFERENT quaternion with a synchronized object pool and deliberately test changed quaternion arithmetic, wrong pool indexing, changed string recipe and source-tree overlay without original overwrite.

The exact real 1,276-file candidate and original-recovered Java remain private; public GitHub contains test tooling and sanitized digests only. The next acceptance stage is to make the five-class joint source build reproducible with a strict R168 verifier, then recover the real rs/x/e Packet source and reduce full client compilation blockers. Do not claim original Packet semantics or a full v309 client build from this math-subsystem result.
