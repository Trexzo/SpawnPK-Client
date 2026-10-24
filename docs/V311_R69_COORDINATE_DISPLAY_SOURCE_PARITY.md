# Original SpawnPK v311 R69 — independently source-built 40-class coordinate/display island

**Audit date:** 2026-10-23. Original binary authority is the exact owner-provided `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Original client JAR, reconstructed private Java, compiled original-named game classfiles and the original-versus-rebuilt behavior harness remain **OFF public GitHub**.

## New authentically source-recovered classes

| Original v311 class | Original SHA-256 | Independently Java9-compiled SHA-256 | Exact original symbolic JVM instruction parity |
| --- | --- | --- | ---: |
| `rs/runelite/a/i.class` — immutable two-coordinate value object | `5c3d2a181d9456ae6370e7e13f53ba5f760cf9fdf2e1dadc15e0b254e10c80e1` | `4b93b7087dd4714134cbdb1faeb0b9bd236745e410d240d740dc9596bfcf8a64` | **89/89** |
| `rs/runelite/a/b.class` — display constants and `Dimension` registry | `a85d59c26bc81d780966c59f4de03fd3512b12a6c8bd95f3a8249b5f0685c4fb` | `50d96315edf0e7e601fca648ea4f475e615733aefa799fc5bfc8849a170d039f` | **10/10** |
| **New** | | | **2 classes / 99 instructions** |

Both classes have **no external original project-class dependencies** in classfile constant-pool metadata. The independent Java9 compiler output matches original-named method/field declarations and descriptors, complete original ordered JVM opcodes, exact original byte offsets, branches, and resolved method/field symbolic operands (only numeric constant-pool indexes normalized).

The value-object `toString()` uses Java9 `invokedynamic`; the verifier additionally verifies the **complete original `StringConcatFactory` bootstrap recipe** after normalizing numeric constant-pool references. The display constants, float/double numeric `ConstantValue` attributes as rendered by `javap -constants`, and the static `Dimension` constructor agree. Original and independently built **complete classfile SHA-256 values differ**, and byte-identical StackMapTable/annotations/attribute parity is **not asserted**.

## Fully closed 40-source independent compilation

Together with the **38 previous accepted** R67 private source reconstructions, these two Java sources compile with **one `javac --release 9 -proc:none -g:none` invocation** using an empty original-game binary classpath and separate empty sourcepath. The same reviewed **disposable compile-only alias** for original `rs/k/c` is used to resolve the original `rs.k.c` class/package conflict, and original JVM class identities are restored in *copied* emitted classfile metadata before comparison. Canonical private Java sources and original JAR are unmodified.

The private verifier attests **40 source-backed Java9 classfiles**, **4,022/4,022 ordered original symbolic JVM instruction matches**, **38/38 earlier original-name compiled class SHA fingerprints unchanged**, **ZERO declaration-only source stubs** and **ZERO missing explicit project-class references** (not dynamic reflection/assets/native closure).

## Original-versus-independent-build runtime checks

A private Java21 process loads original-JAR classes and the independent Java9 class output with isolated `URLClassLoader` instances. The new `rs/runelite/a/i` and `rs/runelite/a/b` probe matched **160/160 original-versus-rebuilt labeled behavior scenarios**: 12×12 coordinate pair inputs including integer extremes, `Math.hypot` distance narrowing, `equals()` and wrong-instance comparisons, hash codes, `toString()` recipe, default display constants and bit-exact floating-point constants, and null distance exception. The previous **118/118** original-vs-rebuilt renderer, scene and geometry scenarios also passed: total **278/278**.

Five deliberate **fail-closed negative private tests** passed:

1. Changed Java source SHA refused before rebuilding.
2. Missing source class refused by exact source set.
3. Wrong original whole-JAR authority refused.
4. Unreviewed alias identity refused.
5. Changed source Java code **with both source and rebuilt class SHA-256 pins updated** refused by exact original JVM instruction comparison.

The self-contained owner-private ZIP `SpawnPK-v311-R69-Renderer-Point-40-Class-Private-Sources.zip`, SHA-256 **`000be3389c2a8c3e861abf4daf80f908232b13a2b197d7f87b20ed61520d158a`**, was clean-extracted and replayed through its complete standalone original-versus-source verifier successfully. All five negative tests passed against the original extracted working source; a second negative-suite run from the clean extraction exceeded the execution limit and is **not** represented as separately complete. The private ZIP has **40 Java sources**, SHA manifests, verifier, probes and negative cases; **no original game JAR/classfiles/assets/fonts/credentials**. This archive is NOT distributed on GitHub.

## Cumulative accounting, public synthetic tests and limitations

Previously accepted R67: **67 distinct original-v311 recovered classes / 5,131 matching original JVM instructions** across separately verified source records. Adding these **two genuinely new classes / 99 instructions** yields **69 distinct accepted classes / 5,230 original instruction matches across separate source-build records**. This does **not** mean 69 compiled together; the largest currently fully dependency-closed combined build is **40 original sources / 4,022 instructions**.

[Unrelated synthetic Java9 coordinate/display regression](../tests/test_v311_synthetic_coordinate_display_parity.py) exercises full source-JVM parity, original-vs-rebuilt toy value behavior, constant-value drift detection, and mutation/missing-source refusal. It uses **no proprietary original client classes/source**. The preceding R67 hosted CI failure was traced to a **synthetic test expecting the wrong exception type**, corrected by commit `a97019ff` without changing the existing verifier's fail-closed collision guard; the corrected R67 head passed all eight Recovery CI jobs and Windows source-safety checks.

The separate `rs/I` + six scene-tile class source island remains **provisional**, excluded from accepted counts because `rs/k/e` and `rs/a/a` original source dependencies remain unresolved. No all-1,184-class source build, exact full original classfile binary equality, original GUI/OpenGL acceptance or authenticated gameplay is claimed. Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT, UNMERGED**.
