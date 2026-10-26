# Original SpawnPK v311 — R126 four NEW nested spellbook / mode JVM class identities

**Owner original authority:** v311 client JAR SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`; 2026-10-24. Original client JAR, owner-private reconstructed Java source, compile transforms/verifiers and compiled game/vendor binaries remain **OFF public GitHub**.

## Four genuinely NEW, original-named, source-generated JVM outputs

| Owner original class | Contents | Original class SHA256 | Rebuilt class SHA256 | Exact original symbolic JVM instructions |
| --- | --- | --- | --- | ---: |
| `rs/n/c/ap$a.class` | COMBAT / TELEPORT / UTILITY spell categories | `884186742e7d92489d6634e8cb6d0012ee5e8ba71bcc272c339bed4a8a9ee7df` | `296f58413e85cde83941c4d7d2ac589a6207614cfb03e12f8b5e4f9da7856991` | **50/50** |
| `rs/n/c/ap$b.class` | 41 original spells; exact spell ID, required level, category and lookup by spell ID | `d93b66584019f930d6d14cecd69f9611c579300df1031835211cf879cf25fc74` | `7b9cdeeed9a59496d78a65a019b46b9afdfe682e3996d6ac915892e7139a15a8` | **586/586** |
| `rs/n/c/ap$c.class` | MODERN / LUNAR / ANCIENTS magic modes | `a4b10c2b2a46602227f2de4c73d1bffde8029a1c354496fa80650c3c0a770c08` | `4a64b3679d60cfe3e8645d73876b5049665a88e1f7040f50991b47f37fd2805b` | **50/50** |
| `rs/u/a$a.class` | LEFT / RIGHT / NORMAL mode enum | `620b930d1b80981b3943b4e599fd1b9b2d64742dc2d3354d1bd8233bf555a389` | `2f72806cced4e8160a536d332f8b018c7cfa1159e049ac6328cc7649dac3b583` | **50/50** |
| **R126 genuinely NEW** | | | | **4 classes / 736 exact instructions** |

The 41 spell identities and individual ID/level/category data derive from the owner's SHA-pinned original Java9 JVM static initializer, NOT inferred game facts. A single `javac --release 9 -proc:none -g:none` invocation accepts exactly **two private Java sources** and an **EMPTY compiler classpath/sourcepath**, producing two temporary donor outer classfiles `rs/n/c/ap.class` and `rs/u/a.class` and four nested enum JVM outputs. Both **donor OUTER classfiles are DISCARDED**: neither original parent outer is recovered or counted. This is a source-recovered nested-class island, NOT a whole original `rs/n/c/ap` or `rs/u/a` source rebuild. There are zero original game/vendor compiler binaries, fake implementation stubs or private game assets.

Original obfuscated constant field/helper identities, nested type names and the category field references inside the spell class are inverse-restored on COPIED classfile constant-pool/member metadata. Strict raw executable **Code attribute payload SHA-256 multiset** is identical before/after each transform (no `Code` or exception handler edits). Original-vs-source-generated `javap -p -s -c` checks method/field declarations, descriptors, byte offsets, symbolic operands and ordered JVM instructions **736/736 exact**. Full classfile binary byte-identity and authentic author-written original Java text are **NOT** claimed.

### Bounded behavior parity with an explicit reflection mismatch

A headless original-JAR baseline vs rebuilt classes (running entirely WITHOUT owner JAR as runtime fallback) matches **63/63 bounded functional observations**. It checks all 41 spell enum names, ordinals, spell IDs, levels, categories, `a(int)` valid and missing lookup behavior, categories, spellbook modes, direction modes, values() copy semantics and **valid** valueOf.

**Important NOT YET ACCEPTED:** Because original `rs/n/c/ap` and `rs/u/a` outer owners are not source recovered, mixing rebuilt nested enum classes with the original owner JAR can trigger `IncompatibleClassChangeError` on `getEnclosingClass()` and *invalid* enum `valueOf` through Java's enclosing-class reflection. This was reproduced and is NOT hidden by the 63/63 bounded acceptance. Thus no complete Java reflection/exceptions/outer-class static runtime closure claim. These metadata-sensitive cases await recovering genuine outer-owner source.

### Clean-extracted original-JAR certification and mutation rejection

Private owner-source ZIP `SpawnPK-v311-R126-Spellbook-4-Class-Private-Sources.zip`: SHA256 **`030b244a03b0e6be0c18c2ea11039bcf6023414e715479c1e40166331a72780f`**, **15,318 bytes / 10 ZIP entries**. It contains only owner-private Java source, original/built class SHA pins, a bounded Java probe, helper/verifier scripts and README; **NO original game JAR, compiled game/vendor binary classfiles, assets or credentials**, and remains owner-private **OFF GitHub**.

Independent **fresh archive extraction** followed by verified original authority SHA, exact Java source/tool/probe hashes, exact 4 selected classfile identities and compiled hash pins, 736/736 original symbolic JVM instruction identity, 63/63 bounded behavior observations **without owner JAR fallback**, and **8/8 deliberate invalid cases REFUSED**. Negative tests include altered/missing/unreviewed source, changed metadata transformer or probe, inflated class ledger, wrong original JAR pin, and **actual change to the Java enum initializer order AFTER BOTH candidate Java source SHA and new built class SHA were repinned**; original-JAR symbolic JVM instruction parity still rejects the mutation.

The [public synthetic-only Java9 nested spell-table regression](../tests/test_v311_synthetic_spell_table_island.py) must use invented toy data, never actual recovered spell constants or code. Public hosted CI is an independent safety check, **not owner-original private parity certification**.

### Accurate ledger and blockers

- R125 accepted cumulative distinct ledger: **125 / 1,184 original classes and 10,470 original JVM instructions**, across SEPARATE private source islands.
- R126 adds **four NEW original class identities / 736 NEW exact original instructions**.
- New **cumulative DISTINCT original-v311 acceptance: 129 / 1,184 original JVM classes and 11,206 exact original matching JVM instructions ACROSS separate privately verified builds**.
- Largest ONE integrated original-named source build remains R124 **94 classfile outputs / 9,153 accounted original instructions**. No 129-class common compiler build is claimed.
- Original `rs/n/c/ap` and `rs/u/a` **parent classes remain missing**; their nested enums are transitive steps toward original `rs/f/a`, whose **DIRECT** accepted dependencies remain **6/11** (R125). Original scene model `rs/a/a` remains **7/14**, renderer `rs/k/e` **17/36** accepted direct dependencies. Seven provisional tile types remain excluded. No complete original client, native graphics, runtime UI/gameplay or full classfile byte identity certification.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**. No manual gameplay tests are required for this limited source island.
