# R174 — nine additional original v309 Packet endian readers

Client-side original Java source recovery, stacked on R173 #1064. The actual original class is rs/x/e.class from private SHA-pinned original v309 client JAR. No original proprietary Java/JAR is published in GitHub.

Nine recovered original JVM method bodies, all int() variants:

| Method | Purpose | Original instructions matched |
|---|---|---:|
| S() | Little-endian unsigned 16-bit | 28 |
| T() | 16-bit modified low byte, high-first | 30 |
| U() | 16-bit modified low byte, low-first | 30 |
| V() | Little-endian signed 16-bit | 37 |
| W() | Modified signed 16-bit | 39 |
| X() | Alternate mixed-endian 32-bit | 52 |
| Y() | Second alternate mixed-endian 32-bit | 52 |
| C() | Big-endian 24-bit integer | 40 |
| D() | Big-endian 32-bit integer | 52 |
| **Added** | | **360/360** |

R173 separately verified 34 original method bodies and 611 JVM instructions. **All 43 now compile together in one PRIVATE original-named Java source class and match 971/971 original JVM instructions.** Independent private javac --release 9 and javap -v inspection of the original versus rebuilt class confirms identical selected method access flags, method stack/local/argument limits, resolved instruction operands and bytecode offsets. This is method-level evidence only; the complete original Packet class and rs/a superclass are still missing.

## Real private inputs and evidence

- Original v309 JAR SHA-256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`
- Original Packet rs/x/e.class SHA-256: `b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2`
- New private 43-method Java source ZIP SHA-256: `e786d0bfe26680014fa848e4a78539292378ffb3e939c540361964e76a38e254`
- Independent private 43-method verification report SHA-256: `03d537d59ad4a3348feb9c5b655bc07bafe00b659e501e3e21a66473f3ec1269`

R174's public verifier first requires the exact R173 34-method proof on the same pinned private JAR/Java source, then independently recompiles and verifies all 43 selected method identities and 971 JVM instructions under an empty original/external classpath. Synthetic Ubuntu/Windows CI covers nine additional Java methods, altered arithmetic and source-hash/count rejection. No original game source or binaries enter hosted CI.

**Not yet done:** The Packet superclass, constructors, remaining original Packet routines, pool/networking and entire class ABI remain unresolved. Do NOT add partial Packet Java to the canonical client source tree (still 1,276 Java files). The last whole-client JDK-only javac error count (2,339) has not been rerun and cannot be reduced by this private partial source alone. R174's exact private GitHub verifier CLI replay is separate from the independent private javap 43-method comparison. Source publishing rights require approval.
