# Official v311 R60 — connected scene-foundation Java source recovery

**Evidence date: 2026-10-22.** User-supplied original v311 client JAR remains private and is pinned to SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`.

## Four additional authentic original Java source reconstructions

| Original class | Original SHA-256 | Independently compiled SHA-256 | Exact original JVM instructions |
| --- | --- | --- | ---: |
| `rs/t.class` | `430c61233ef1d46a3dadbe4947a3d4d17019db2bc1d4678dc732623ea1b3274f` | `334fb23b8bf2ad12c1ef03d8e881c39d5cceda51e03a830c057bd6980799bb54` | 24/24 |
| `rs/Q.class` | `bbab3088f0408c65c55565d78d26875e433aa7aae1674990b039170dee95ff94` | `ce8062ee0dbe944851e738a36cbef7789e0f0a888014956b847d881174ab4133` | 3/3 |
| `rs/G.class` | `2754c9b74c5539e7a9088c5ce2a944d0d774c47cb02a13a2b7f1b22ea98b21fe` | `7be13829178a55b2553ecaed8e2646f59da40c945b7148f7e9d9727d0e750257` | 3/3 |
| `rs/S.class` | `770eae44d02c4345c247b37516ddfbbb9be04f88f9edf97c3b4ccb33a2645880` | `f08c8f92386297332aedffbc330eaf1516dd3af17d3df5403c6bf87cd62b8849` | 146/146 |
| **New** | | | **176/176** |

- `rs/t` is a doubly-linked node foundation directly required by the original tile class `rs/H`; `rs/Q` is the parent for several tile entity-holder classes. `rs/G` and `rs/S` are data structures explicitly referenced by original scene renderer `rs/V`. The 18-field `rs/G` and 4-integer-per-entry `rs/S` sources match constructor and accessor instruction order.
- The above source files **plus the 23 verified R56 sources** compiled **together in one fresh `javac --release 9 -proc:none -g:none` build**, with an empty original-game binary classpath and sourcepath. **All 27 classfiles, 2,034/2,034 ordered JVM opcodes, byte offsets, symbolic method/field operands and declarations matched** the exact original v311 class surfaces (only numeric constant-pool indexes normalized); existing 23 independently compiled source fingerprints remained unchanged.
- Explicit project-class dependency closure against all 1,184 original `rs/` classes was checked: **zero missing explicit `rs/` dependencies across the 27 selected classes**. Dynamic, reflection, resource and native closure remain unverified.
- Fourteen additional **original-JAR versus independent-source JVM behavior transcript lines** matched exactly: linked-node unlink/retry/invalid-link exception, default/mutated record fields, 4-integer data access and mutation, sentinel flags and bounds exceptions. Prior private headless panel, font, progress, scrollbar, timer, buffer-pool, scene-record tests and invokedynamic bootstrap parity passed again.
- Private reproducible archive: `SpawnPK-v311-R60-Scene-Foundation-27-Class-Private-Sources.zip`, SHA-256 `20070519483e67496f85183e10d638f61c7e0ad006e6827f17f9906631e9fd28`. It excludes the official game JAR, original compiled game classes, fonts, caches, credentials and login state. Its clean-extraction self-verifier passed; it refuses a deliberately changed `rs/S` implementation and a wrong original JAR hash.

## Cumulative progress and limits

**60 distinct reconstructed original v311 Java classes / 3,288 matching original ordered JVM instructions across SEPARATE source-build records.** The largest presently combined build is **27 classes / 2,034 matching instructions**, not a single 60-class compilation, full 1,184-class client, classfile byte identity or authenticated game rendering.

Original `rs/H` has **8 direct project-class dependencies**: two (`rs/t` and `rs/J`) are now in the 27-class source build; six (`rs/I`, `rs/T`, `rs/U`, `rs/l`, `rs/m`, `rs/n`) remain missing. Original `rs/V` has **25 unique direct project-class dependencies**, four included in this selected source set (`rs/G`, `rs/J`, `rs/S`, `rs/t`); the others include large client/renderer subsystems. Note that original `rs/t` is also a Java class while other original source names form the `rs/t/` package, so a **reviewed alias strategy** remains necessary before a full source tree can be compiled. Neither original `rs/H` nor `rs/V` has been source-rebuilt in R60.

The public hosted [synthetic scene-foundation parity regression](../tests/test_v311_synthetic_scene_foundation_source_parity.py) uses unrelated toy Java9 node/record subclasses and checks a three-source dependency closure, JVM instruction parity, behavioral equality, and intentional mutation/missing-dependency refusals. Hosted CI **does not** use the private original JAR or reconstructed Java. Keep PR #1142 **draft and unmerged**; no manual game launch is appropriate for this source-only checkpoint.
