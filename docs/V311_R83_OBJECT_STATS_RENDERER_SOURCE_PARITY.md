# Original v311 R83 — closed 54-source object/stats/Swing renderer island

**Private original authority:** owner-supplied `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Neither original client binary, recovered game Java, compiled original-named classfiles, nor private original-vs-rebuilt probe is in this public repository.

## Three new, unique independently source-reconstructed classes

| Original JVM class | Original class SHA-256 | Independent source-built class SHA-256 | Exact original JVM instructions |
| --- | --- | --- | ---: |
| `rs/runelite/events/ObjectInteraction.class` | `8662868d1355ee5754ac0febd484aa128507c91381f64d2cee14e43d4d2b7f47` | `f25e2b2ddf9a6ee0e12ac07a6457ca93a888999a5a82f308b3ccb24c107dce7a` | **150/150** |
| `rs/plugins/r/a/b.class` | `e3746e70e9845ece666fbd893038de2c305477aec41360e2c7e7d816141086ef` | `ee6a659e414783b5e53ed153e6c59b438206fc25e20059734cf25538ab97dd40` | **195/195** |
| `rs/gui/b/a/e.class` | `b8029c4109584a37941af3d430f839217d11a677f0933ce016c851f8fd848d52` | `cdcdc1a84b2b8a73656e2ac8dbf6d80665d827f908e8cc12af51ee061d7addfd` | **80/80** |
| **Newly accepted total** | | | **3 classes / 425 instructions** |

The three new classes passed exact comparisons of original JVM class declarations, methods/descriptors, ordered original instruction opcodes, byte offsets, branch targets, exception metadata in the existing `javap` scope, and resolved symbolic operands (normalizing only numeric constant-pool indexes). Java9 `StringConcatFactory` bootstrap recipes for `ObjectInteraction` and the statistics holder agree. The Swing renderer's Java `ConstantValue` field metadata was separately compared. The original full classfile binary hashes are *not* identical and comprehensive JVM attribute/StackMapTable identity is not claimed.

## Authentically compiled, original-name, 54-class island

The private R80 baseline contains **51 independently certified sources and 5,368 exact original JVM instruction comparisons**. R83 adds three newly reconstructed sources; a single `javac --release 9 -proc:none -g:none` invocation now produces **54 source-backed Java9 classfiles with 5,793 original JVM instructions accounted for**, **all 51 previous R80 rebuilt classfile SHA-256 fingerprints unchanged**, zero temporary declaration-only Java stubs, and zero missing explicit original project-class dependencies under the SHA-pinned original constant-pool/descriptor scanner. The original client JAR and game classes are never included on the source compiler classpath.

The existing `rs/k/c` class/package collision uses only the previously reviewed disposable compile-only source alias and inverse-restoration on copied rebuilt classfile JVM names. Canonical private sources and original binary are unchanged.

**Important comparison qualification:** to bound replay time, this R83 clean-extracted verifier checks exact SHA pins of **all 54 original and rebuilt classes**, exact source fingerprints, original project-class static dependency closure, and independently compares the **three new classes' 425/425 actual original JVM symbolic instructions**. It reuses R80's certified original instruction evidence for the 51 old classes because their compiled byte identities are unchanged, rather than pretending to have repeated a fresh 54-class `javap` diff in one run. Thus the **5,793/5,793** combined statement is an authenticated composition of **R80 parity plus unchanged compiled fingerprints plus new R83 parity**, not 108 fresh disassemblies.

## JDK-only runtime behavior and refusals

The newly introduced original-vs-rebuilt probe checks **48/48 matching cases**, including object interaction IDs, negative/overflowed coordinates, equality, hash/formatting, plugin success counters and float raw-bit ratios, and Swing list-cell colors, selected items, mismatched arrays and null-input exception behavior. The **942 earlier R80 cases were already certified** and **were not rerun** in this bounded R83 replay; do not report a fresh 990-case runtime suite.

The owner-private ZIP was independently clean-extracted; its R83 verifier passed the 54-source SHA/classfile/closure checks, 425 new instruction comparisons, full preserved R80 source identity and 48 new behavior cases. From that clean extraction, the following **five/five deliberate fail-closed trials** each passed:

1. Modified owner-private Java source refused on its SHA pin.
2. Missing original-named source refused before compiling.
3. Wrong whole-original JAR SHA refused.
4. Unreviewed compile alias mapping refused.
5. Changed actual JVM instructions refused **after repinning both reconstructed source and recompiled class SHA values**.

Owner-only archive: `SpawnPK-v311-R83-Object-Stats-UI-54-Class-Private-Sources.zip`, SHA-256 **`5467c630c2394aefda8edc02071356a0b5afff1fc31f3e274efb868cf4b12dcf`**. It contains 54 reconstructed original Java files, exact original/source/rebuilt SHA manifests, standalone verifier and probes, and five refusal tests; **NO original client JAR, game classfiles, font binaries, accounts or game assets**. Do not upload this archive to public GitHub.

## Count ledger and exclusions

R80 accepted cumulative: **80 distinct recovered original classes / 6,576 exact matching original JVM instructions** across *separate previously accepted source build records*. The three R83 new classes add **3 classes / 425 instructions**, giving **83 distinct accepted original-v311 source classes / 7,001 original JVM instruction matches cumulatively**. The **largest single dependency-closed source compilation is 54 original classes / 5,793 instructions**, not a single 83-class compile.

Three attempted source candidates were reviewed: `rs/runelite/a/a` is **already counted** in the accepted R80 source inventory and was not double-counted; `rs/runelite/a/j$c` has a missing outer `rs/runelite/a/j` class dependency and was not accepted; `rs/ui/components/a/n` would introduce an unreviewed second class/package collision with `rs/ui/components/a` and was excluded. This records why neither provisional source nor duplicate classes inflate the accepted count.

The seven original `rs/I` / tile sources remain **provisional** due unrecovered renderer `rs/k/e` and scene-model `rs/a/a` dependencies. Full 1,184-class client source closure, runtime rendering/gameplay acceptance, reflection/native/resources and complete original binary identity are not established.

[Public synthetic-only tests](../tests/test_v311_synthetic_object_stats_renderer_parity.py) use independently authored toy Java and validate generic JVM parity and fail-closed behavior. Hosted GitHub CI does **not** have the owner-private original game JAR, sources or private verification fixtures. Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**.
