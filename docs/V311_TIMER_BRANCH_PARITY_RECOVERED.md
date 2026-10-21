# Original v311 timer: precise branch-parity recovery of `rs/y/a.class`

**2026-10-21.** Source evidence below was reproduced using the exact user-uploaded official `client(20261021-111920).jar`, whole-JAR SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The original binary, Java reconstructed from bytecode, compiled classfile and behavior harness are **private** and not committed to this public repository.

## Previously excluded timer now passes original-JVM verification

The [35-class source milestone](V311_THIRTYFIVE_CONNECTED_SOURCE_ISLAND.md) explicitly excluded `rs/y/a` because an apparently equivalent Java ternary returned the opposite conditional branch shape despite matching JVM instruction **count**.

A fresh independent examination of the exact original class disassembly and a standalone Java 9 compilation identified the compiler-sensitive source distinction: placing **zero remaining time on the first ternary arm of a negated active predicate** rather than the second arm produces the original conditional `ifne` at byte offset 4, branching to the remaining-time arithmetic at byte offset 11. The earlier Java candidate instead produced `ifeq` to offset 23. Both variants are similar semantically but **not original instruction/offset parity**. This is a source shape recovery witness, not proof of the exact original author-written text.

The privately reconstructed `rs/y/a.java`, along with locally independently reconstructed dependency `rs/y/b.java` and `rs/y/c.java`, compiled under `javac --release 9 -proc:none -g:none` with no original game binary or source on the compilation classpath. A direct original-vs-private-recompiled `javap -c -p -s` comparison confirmed all declarations, descriptors, ordered instructions, original byte offsets, branches and resolved symbolic operands matched after normalizing **only numeric constant-pool indexes and their padding**.

| Original class | Original class SHA-256 | Recompiled private class SHA-256 | Matching JVM instructions |
|---|---|---|---:|
| `rs/y/a.class` | `1eecae78644e2a02f633cf3aac53ca12d2ea46de858b013abdece8c1a7c579e4` | `fa55105116e3a2f61aaa25466d6ca3934ea45e1fcb923d718fb99235a35320b1` | **35/35** |
| `rs/y/b.class` | `5535343f6f7fe8d852b0e42f1d4350e3baf75b2be312fbe9cbcb9f04dd4bfc32` | `e2f55eaacb726c8785ee66c655978d27e15ae77143f00eb9df41f08014de3bc4` | **3/3** |
| `rs/y/c.class` | `98c06b541407a72771e6e172130b781eb799da4259abbd45748b9f08c0e3b8a8` | `463be801ff0c0ec4bc8db1e68656c36d4552554f6a107870f1ccb6b3872873fd` | **0/0**, interface declarations/descriptors |

For `rs/y/b` and `rs/y/c`, private compiled SHA-256s equal the ones previously reported in the 31-source island. This independent three-class compilation also reproduces those previous results.

## Original-versus-recompiled offline behavior

Both exact original and rebuilt classes were separately loaded using JDK `URLClassLoader` reflection. A bounded duration-invariant probe compared three constructor/reset scenarios: zero duration (inactive, remaining=0), negative duration (inactive, remaining=0) and a long positive duration (active, remaining time within the expected positive range). Original and independent-source outputs **matched all scenarios**. Wall-clock elapsed times were **not** equated, and this does not claim complete timer/runtime parity or gameplay verification.

## New public diagnostic regression

`src/spk_recovery/source_parity_diagnostic.py` is a refusal-only helper wired into the existing SHA-pinned `standalone_source_parity.py`. On a full original-vs-rebuilt disassembly mismatch, it reports the **first differing method region, instruction offset, opcode and reason**, without outputting original bytecode, field/method symbolic operands, literal constants or private source. The verifier continues to reject any difference; there is no approximate-match acceptance.

`tests/test_v311_source_parity_diagnostic.py` compiles independent **synthetic Java 9 timer-branch variants** and asserts that the inversion reports the actual `ifne` vs `ifeq` at offset 4, while complete identity reports no difference. Additional tests prove literal operand mismatch descriptions never expose their values and truncated instruction streams refuse. Hosted CI does **not** possess the real v311 reconstructed timer source.

**Strict status:** this confirms a separately independently rebuilt timer with **35 exact original JVM instructions**, plus its original two support class dependencies. The prior 35-source combined build remains the last fully evidenced large single-source island. A **36-class combined build including `rs/y/a` has not been rerun or independently certified**, so do not combine the counts to claim 36 fully accepted classes. Exact original classfile bytes/attributes, dynamic references, original-source provenance and game/runtime acceptance remain unproven.

Next recovery target: either merge the independently verified timer into the private connected source-island authority with a fresh full-class build and manifest, or tackle the pending original `rs/ui/components/x` UI renderer and its `rs/ui/components/w` interface dependency with the same fail-closed bytecode parity requirements.
