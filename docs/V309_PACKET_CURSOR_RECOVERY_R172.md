# R172 — 22 original-v309 Packet Java methods reconstructed

Client-only original v309 source recovery, stacked on R171 #1062. Work on actual original client Java, not a server emulator. **All original source and JAR bytes remain PRIVATE and are not placed in GitHub or CI.**

## Independent private JVM evidence

The exact original class is `rs/x/e.class` SHA-256 `b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2` in original v309 client JAR SHA-256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

R171 independently reconstructed six reader methods with **186 matching JVM instructions**. R172 extends the same one-class Java9 partial source with **16 further original source method bodies**, reproducing **123 additional original JVM instructions**, for **22 selected methods / 309 original decoded JVM instructions** together.

| Newly recovered original method | Function | Original JVM instructions |
| --- | --- | ---: |
| `h():int` | cursor snapshot through local slot | 5 |
| `i():void` | cursor reset | 4 |
| `j():int`, `k():int` | original small integer constants | 2 + 2 |
| `z():byte` | signed postincrement byte read | 11 |
| `J():void` | initialize bit position from cursor | 7 |
| `K():void` | convert bit position back to byte cursor | 9 |
| `Z():int`, `aa():int` | cursor accessors | 3 + 3 |
| `ab():int` | original auxiliary position field getter | 3 |
| `ac():byte[]` | original internal buffer getter | 3 |
| `N():int` | byte-minus-128 masked read | 15 |
| `O():int` | negated unsigned-byte read | 14 |
| `P():int` | 128-minus-byte masked read | 15 |
| `Q():byte` | negated signed-byte read | 13 |
| `R():byte` | modified signed-byte read | 14 |
| **Added R172** | **16 new methods** | **123/123** |

The private original-named Java file was independently compiled with `javac --release 9 -g:none -proc:none`, no original client JAR or external class binaries on its compiler classpath. Private original/rebuilt `javap -p -s -c` comparisons match original instruction offsets, opcodes, constants and resolved field targets for each selected method. This retains R171's 6/186 previous proofs. The real entire partial class still has missing superclass, additional original Packet methods, packet pool and networking behaviors; **not** complete original Packet classfile/StackMap/runtime equivalence.

### Private source pins

- One-class 22-method original-name Java ZIP SHA256: **`5735e509e95be5b0b3e587768df17f47afa979fab2eeeacb3f1c3312548de257`**.
- Exact Java source text SHA256: **`cefc134312418ea18cdfa1ad4c3e84699d1c53815a45b6c5462be398d37d22a8`**.

The 22-method source ZIP contains only the partial original-name Java source candidate; it is not a complete client source distribution or an approved original-derived source release.

## GitHub verification

New private R172 verifier reuses the **exact same SHA-pinned R171 six-method proof** first, then independently recompiles the expanded Java class with empty original/external binary classpath and compares all 22 selected original-v309 JVM method bodies with the strict existing source-vs-original code inspector. The exact private evidence must match both original class/JAR digests, **six legacy/186 instructions and 16 additional/123 instructions**. It rejects changed instructions, class/source hash drift and missing method identities. The original/rebuilt one-class method instruction set must contain the selected 22 members.

Hosted Ubuntu/Windows CI compiles an **entirely synthetic** different Packet class with 22 selected method names but deliberately different cursor constants/algorithms from the real original, and verifies exact synthetic source recompilation and negative mutation/expected-count/SHA vetoes. R171 is rerun for regressions. Original proprietary client Java/class bytes never enter GitHub.

## Completion boundary

Partial Packet Java is not installed into canonical private `recovered-source/v309/src`, which remains **1,276 original candidate client Java files** from R167. The last independent full-JDK-only compiler measurement is **2,339 javac errors**, not rerun for this partial class. The older provisional normalized-binary dependency capsule's 516-error result is a different measurement and is not comparable.

Original Packet `rs/a` superclass, missing constructors, Packet pooling, data transformations and numerous other methods remain. Recover and verify those before placing the entire Packet Java class into the canonical tree. This PR stays draft until exact-head CI, exact original-private verifier replay and complete source/rights checks.
