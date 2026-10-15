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
