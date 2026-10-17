# R185 — private LootTracker Java-source reconstruction slice

Concrete source changes against the uploaded **third-party decompilation**, not the original exact-v309 binary.

## Files and behavior

Four Java model classes were rewritten to remove Lombok requirements and supply explicit Java implementations:

- `rs/plugins/loottracker/ItemStack.java`: two-argument constructor, accessors, equality/hash.
- `rs/plugins/loottracker/LootTrackerItem.java`: five-argument constructor, accessors, mutators, equality/hash; existing total-price/pricing-copy methods retained.
- `rs/plugins/loottracker/LootReceived.java`: explicit accessors and equality/hash.
- `rs/plugins/loottracker/LootTrackerPriceType.java`: explicit enum constructor and accessor.

A fifth baseline file (`LootRecordType.java`) and a new isolated `LootSourceTest.java` are included in the **private** output. It compiles all six sources with `javac --release 9 -proc:none` (empty external dependencies) and executes the model tests successfully (`LOOT_SOURCE_TEST_PASS`).

## Private delivery

Private archive: `SpawnPK_v309_LOOT_SOURCE_R5_PRIVATE.zip` (delivered in the conversation, **not published in GitHub**). Contains source files, test and SHA manifest. The current GitHub R184 assembler can apply these four source replacements using individual before/after file SHA approvals against the user's private baseline tree.

## Strict limitations

- This was **not** exact original v309 bytecode recovery. Original-v309 classfiles and complete privately recovered candidate were not available for parity verification.
- Lombok's generated constructor null-checks, accessor visibility and hash implementation may differ from the explicit implementation. Do not treat the patch as canonical original Java.
- Isolated six-source compilation is not full-client compilation. Do not count it as four complete original-owner recoveries.
- Keep source files private until redistribution rights are verified. Do not auto-merge them into authoritative source tree without review.

Next work: replay on the actual private v309 source snapshot and verify all callers, binary ABI, and strict original classfile method-level parity; prioritize genuinely original methods over repeated subset-count increases.


## R186 extension — LootTrackerRecord source and grouping semantics

Extended the same private model batch to `LootTrackerRecord.java`. Explicitly implements former Lombok accessors and title/type identity while retaining existing record grouping and merge logic. Added explicit constructor null checks for `title` and `type`. The private R6 package contains five edited production Java classes, one unchanged enum and one test harness.

Independently compiled the seven files together with `javac --release 9 -proc:none`, no Lombok or original-client JAR, and executed `LootSourceTest`, including record ignored/visible kill counting, total-price calculation, merge quantity and timestamp propagation, getters, item equality, and price mode. The test passed.

**This is original-candidate source repair, not exact v309 bytecode parity.** The explicit Lombok replacements, including equality/hash details and null validation, require caller ABI and original JVM parity review before acceptance. R186 private artifact name: `SpawnPK_v309_LOOT_SOURCE_R6_PRIVATE.zip`.


## R187 extension — GroundItem and ItemThreshold

The consolidated **R7 private model source archive** adds two more edited client classes, `rs/plugins/grounditems/GroundItem.java` and `ItemThreshold.java`, with explicit field accessors and GroundItem mutators replacing Lombok-generated methods. It retains the five edited LootTracker classes, the unchanged LootRecordType enum, and adds a second behavioral test. Nine Java files compile together with Java 9 language/API compatibility and no third-party dependency jars; `LootSourceTest` and `GroundModelTest` execute successfully.

Tests cover item value and high-alch arithmetic, mutable price/quantity, state reset, quantity threshold comparison, LootTracker grouping and merge, timestamps, and item price modes. **No original-v309 bytecode parity is claimed.**

Artifact: `SpawnPK_v309_MODEL_SOURCE_R7_PRIVATE.zip`. The archive is delivered privately, with per-source-file hashes and both test sources. It should only be applied through reviewed private source overlays; do not assume that these seven Lombok replacement classes preserve bytecode parity with the original v309 client.


## R187 complete uploaded-source javac A/B replay

Replayed **the complete 1,274 Java files** from the uploaded third-party client decompilation on local JDK 21.0.12.1 with the same command and no external JARs in both runs:

```
javac -proc:none -g:none -encoding UTF-8 -Xmaxerrs 3000 -d <isolated-output> <all-1274-java-files>
```

| Identical build profile | Baseline uploaded sources | R7 with seven model source replacements |
|---|---:|---:|
| javac diagnostic errors | 2,391 | 2,109 |
| warnings | 9 | 9 |
| `cannot find symbol` occurrences | 1,711 | 1,485 |
| `package lombok does not exist` occurrences | 54 | 36 |

**Net change: -282 compiler diagnostics**, not 282 independent bug fixes. Most of the reduction is cascading resolution after adding explicit constructors/getters and removing seven classes' Lombok imports. Other external dependencies remain absent. This comparison concerns **the uploaded third-party 1,274-file decompilation**, not the separate 1,279-file original-v309 private recovery snapshot; do not transfer its compiler counts into v309 original-source acceptance.

The private R7 package includes `FULL_TREE_COMPARISON.json` with diagnostic category deltas and SHA-256 of both raw compiler stderr logs. Dedicated model tests for LootTracker and ground-item logic pass. Original-v309 bytecode-equivalent Java source remains unverified.


## R188 — expanded private Java model repair and whole-source replay

Added two additional production Java source repairs to the private R8 package:

- `LootTrackerMapping.java`: replaces Lombok enum all-argument constructor with explicit `LootTrackerMapping(String name)`. This file is checked in the full 1,274-file compiler replay; its external dependencies preclude isolated compilation without extra source.
- `UnitsFormatter.java`: removes Lombok `@SneakyThrows` and uses the overridden `AbstractFormatter.stringToValue(String) throws ParseException` contract directly, without changing error type. Its genuine `rs.config.Units` annotation is included in isolated Java 9 tests. `UnitsFormatterTest` passes.

**Whole-tree same-profile measurements (uploaded candidate only):**

| Full 1,274-file JDK-only javac run | Errors | Warnings |
|---|---:|---:|
| Baseline R4 | 2391 | 9 |
| R7 — seven edited production files | 2109 | 9 |
| R8 — nine edited production files | **2099** | **9** |

R8 represents **292 fewer raw diagnostics** than baseline under the *same* JDK 21.0.12.1 `-proc:none -g:none -encoding UTF-8 -Xmaxerrs 3000` invocation, with no external JARs. This is not 292 new original-method recoveries or a complete client build.

Three isolated Java test programs pass: LootSourceTest, GroundModelTest and UnitsFormatterTest. The complete private R8 package includes reviewed source candidate edits, genuine companion source requirements, tests, source SHA manifest and `FULL_TREE_COMPARISON.json` containing per-profile compiler stderr SHA digests and aggregate deltas.

**Acceptance status remains private/unverified.** The source was derived from the uploaded third-party decompilation rather than recovered from the exact original v309 JAR. Source method parity, cross-call API compatibility, runtime behavior and redistribution authorization all require separate independent verification. Do not merge Java source as exact-v309 authority.


## Full 1,274-file candidate snapshot — privately assembled R8

A private full-source candidate was materialized as `SpawnPK_v309_FULL_SOURCE_R8_PRIVATE.zip`. The ZIP contains `src/**/*.java` (exactly 1,274 sources), `PRIVATE_MANIFEST.json` with per-file SHA-256 and the nine exact before/after changed-source witnesses, plus `FULL_TREE_COMPARISON.json`. A programmatic manifest comparison confirmed **all 1,265 other Java source files are byte-identical** to the uploaded R4 baseline.

This is a complete **candidate source tree**, not a completely compilable or original-v309-verified tree. The R8 JDK-only compiler still reports 2,099 errors. Neither the private archive nor original-derived Java is pushed to GitHub. Any future acceptance must replay against the pinned original v309 JAR and the canonical separately recovered 1,279-source private snapshot.
