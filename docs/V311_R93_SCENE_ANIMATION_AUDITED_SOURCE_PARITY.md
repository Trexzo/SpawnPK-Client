# Original v311 R93 — audited distinct-class count, closed 65-source island

**Date:** 2026-10-23. Owner-private original JAR `client(20261021-111920).jar`, SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Original game JAR, independently reconstructed Java, compiled game classfiles and the authentic original-vs-rebuilt probe remain **OFF GitHub**.

## Three newly accepted originals; one genuinely previously recovered class reintroduced

| Original v311 class | Original class SHA256 | Independently source-built Java9 SHA256 | Matching original JVM instructions | Distinct acceptance |
| --- | --- | --- | ---: | --- |
| `rs/l/c/e.class` — mutable scene entry | `ff31253ad14cfefa7d203717e7f8592e9cb1aea5860b57ca284b809782cf1967` | `13132828b18f08ebd58a9467d6115676afdd48598c94eed66262f07ce13fff93` | **31/31** | NEW |
| `rs/l/i.class` — bounded oscillating counter | `a2432bf901adec672dce2a9d5c29bb7003fc9aa621b3669f687683d144a8fdad` | `4d96d4d91d0f31127811495f6083e20ddf9e88563ad579caca1f922cc8cf2635` | **38/38** | NEW |
| `rs/l/a/a.class` — nine-field fluent animation/state record | `591962ba5486f50fed41052cecfe9d4c9aff2a334358488435163e79699088d8` | `6d4fa746ff28a5b814a456a09fb69cb514f28fcecacf2a7aaffefc32a0e435b8` | **89/89** | NEW |
| `rs/l/e/l.class` — text and default dimensions | `d46e7d533bd95e42ed82d1428014c07e96e5945566e683fa88fa626b5bb6fd19` | `3baeb72ededc1dda69963ff86b9bd550b79161ce5a3b8141b1624c8469b89c51` | **12/12** | ALREADY ACCEPTED R23 |
| **Combined additional build inputs** | | | **170/170** | **3 genuinely new / 158 new instructions** |

**Critical distinct-class audit correction:** The `rs/l/e/l.class` original and rebuilt hashes are **identical to the already accepted R23 evidence** in `docs/V311_TWENTYTHREE_INDEPENDENT_SOURCE_ISLAND.md`. It was absent from the later 61-class R90 source-island build and can legitimately rejoin the source island, but its **one class and twelve instructions cannot be counted again**. A provisional private bundle and response used R94 (94 distinct classes / 7,658 instructions) before this cross-island audit. **Those cumulative figures are superseded.** The correct audited milestone is **R93: 93 distinct accepted classes / 7,646 matching original JVM instructions**. This correction does not invalidate the four source classes' original JVM comparisons, original-versus-rebuilt behavior probes, or source compilation.

## One genuine 65-class independent Java9 build

The 61 R90 private sources and four classes above compiled in one `javac --release 9 -proc:none -g:none` invocation, with no original game binary on the compiler classpath or external sourcepath. The reviewed, disposable `rs/k/c` class/package compile alias was inverse-restored on **copied** generated classfile JVM metadata; canonical Java and original JAR were not modified.

The independent clean-extracted R93 verifier confirms **65 exact original-name classes / 6,450/6,450 original JVM instructions accounted for**, **61/61 previous R90 compiled class SHA fingerprints unchanged**, and freshly verifies **170/170 symbolic instructions** across the four additional sources (158 newly accepted and 12 reintroduced). All original class/member declarations, JVM method descriptors, branch targets, instruction offsets and symbolic operand values match after normalizing only numeric constant-pool indexes. Original-vs-rebuilt `javap -p -constants` declarations match. **No temporary stub source classes or missing explicit original project-class dependencies.** The 6,280 previously accepted R90 instruction comparisons retain certification through identical compiled hashes; they were not fully re-disassembled in R93.

Isolated headless original-JAR-versus-rebuilt JVM behavior matched **150/150 new tested lines**, including null/Unicode string records, mutable scene entries, animation bounds, wrapping/overflow, fluent setters/getters and forced state. These are bounded JVM checks; previously certified behavior cases from R90 were **not freshly rerun** and no game/GUI behavior is claimed.

## Clean-extracted archive, mutation refusals, and limits

The superseding owner-private ZIP `SpawnPK-v311-R93-Scene-Utilities-65-Class-Private-Sources.zip`, SHA-256 **`755d2706ad576e36a880809aec4665e25313d3ea46f4c79a77752099a115c7c8`**, contains exactly 65 reconstructed Java source files, two SHA-pinned manifests, standalone compiler/bytecode verifier, JDK behavior probe and five refusal tests. **No original JAR, compiled game classfiles, fonts, assets, accounts, credentials or original-game binary data. Do not publish private source.**

Independent fresh ZIP extraction passed the full source compilation, all hash/JVM/behavior checks and **five/five deliberately invalid cases**: source modified, source missing, wrong whole-original JAR, unauthorized compile alias and changed JVM instructions refused even after repinning both the candidate Java-source and newly compiled class SHA hashes.

Correct cumulative source recovery: **R90 90 distinct classes / 7,488 original instructions** across separately certified builds **+ 3 newly accepted / 158** = **R93 93 distinct classes / 7,646 instructions**. Largest *single* source-closed compilation is **65 classes / 6,450 instructions**, not all 93 compiled together.

Unaccepted: original `rs/l/e/k` requires a real, verified external GNU Trove compiler dependency; no placeholder stub is authorized. Original `rs/k/e` and `rs/a/a` large dependency chains are unresolved; seven provisional original `rs/I` and tile classes remain excluded. Full 1,184-class source recovery, complete classfile byte identity, native/OpenGL graphics, reflection/resources and live gameplay are unverified.

Public [synthetic-only animation/scene source regression](../tests/test_v311_synthetic_scene_animation_source_parity.py) uses unrelated JDK-only toy sources, not recovered game code. Hosted CI must be independently checked. **Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) DRAFT and UNMERGED.**
