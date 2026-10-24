# Original v311 R64 — 35-class scene-record and renderer-support source island

**Owner-private verification date:** 2026-10-23. Exact owner-provided v311 JAR SHA256: `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Original client JAR, reverse-engineered Java, compiled game classfiles and original-vs-rebuilt JVM probe are private and are **not** published in GitHub.

## Three newly accepted, exact instruction-matching original Java classes

| Original class | Original classfile SHA256 | Independently source-rebuilt Java9 classfile SHA256 | Ordered original JVM instructions |
|---|---|---|---:|
| `rs/a/d.class` — packed 3-int record array | `5793ad7345d7d14b86961310c297fd319d13a23a9353bdb650b9444635b99335` | `b1773d6e4f4b8d92493f3e1bf4fa01656c6e78b44e03416209caa7947e30d3ee` | **105/105** |
| `rs/k/b/c.class` — four-slot renderer lookup | `4ca88e5f2d917dcf27645b854d8100e05663e43988bd7e3ed3503bda22d9a086` | `d4cf039a97356259c88acb035c57aad559a499ba60b2e47753932856538291fa` | **25/25** |
| `rs/gui/b/b/a.class` — GUI state record | `0502c6bbbaf4ad0c42258da4d9860b63db62518e6ab7f41bfd120bc6f877f82b` | `b36b5a1edf446591db7f80c92fd3dd2903dfc4e1b4f4aeebc5ddf70e18dd2b3f` | **23/23** |
| **New total** | | | **153/153** |

These three each have **zero explicit dependencies on other original project classes** in the pinned v311 constant pool. Independently reconstructed Java9 source matches all original method declarations, fields, ordered JVM opcodes, symbolic operands, byte offsets and branch targets after normalizing **only** numeric constant-pool indexes. The original and compiled full classfile SHA fingerprints differ by design; complete original classfile attribute and source-text identity are not claimed.

## One full dependency-closed 35-class source build

The 32 original Java sources already certified in R61 and the three new sources were compiled **together**, in one `javac --release 9 -proc:none -g:none -encoding UTF-8` invocation, with an explicitly empty original-game binary classpath and external sourcepath. Exactly **35 source-backed Java9 classfiles**, **zero declaration-only source stubs**, **zero missing explicit original project-class dependencies**. All 32 prior rebuilt classfile SHA-256 fingerprints match their R61 pins unchanged. The strict fresh private verifier reports **3,251/3,251 exact original symbolic instructions across the 35-class build**.

A separate owner-private Java probe loaded the exact original v311 JAR and reconstructed outputs in distinct JVM classpaths. **36/36 event lines matched** for three-int record creation/assignment/overflow/arithmetic/bounds errors, four-slot indexed reads and fluent setters, and GUI long/int state updates. Behavior transcript SHA256: `26294625e665a7600d87e86befb61daa7dbbbd439137c5f221583e8dd1e38560`. The existing **39/39 matrix** and **22/22 renderer-buffer** cases passed again. These are bounded JDK-only comparisons, not OpenGL, original game launch, network authentication or exhaustive behavior proof.

The private ZIP `SpawnPK-v311-R64-Scene-Renderer-35-Class-Private-Sources.zip` has SHA256 **`3ffd49a5b412c0e26b240c5639a2510c3078cc9be9b1b9d952c04cc0167eb77a`**. A clean extraction replay verified the full 35-source build, all 97 original-vs-rebuilt behavior lines and **four deliberate refusal tests**: changed source SHA, changed JVM instructions even with repinned source/rebuilt class SHA, deleted source class, and corrupted original game JAR. Private artifact includes Java sources, exact hash manifest, probes, fail-closed verifier and README, and excludes original JAR, game classfile outputs, fonts, account data and other game resources.

## Cumulative accounting and acceptance limit

Previously certified R61: **61 distinct original-v311 Java classes / 4,306 matching original JVM instructions** over separate source-build records. Only these three genuinely new classes (**3/153**) are added, yielding **64 distinct accepted classes / 4,459 matching instructions cumulatively**. The largest *single* source-closed build is **35 classes / 3,251 instructions**; 64 were **not** compiled together. Older previously accepted class `rs/t` and `rs/Q` are not counted again.

The separate original tile source group `rs/I` plus six tile candidates remains **provisional** because source dependencies `rs/a/a` and `rs/k/e` are still unrecovered and were replaced by named declaration-only stubs in that other experiment. These seven are **excluded** from accepted totals. Full 1,184-class client compilation, all metadata/StackMapTable parity, reflection/assets/native closure and gameplay are not proven.

Public [synthetic-only Java9 record/source-island regression](../tests/test_v311_synthetic_scene_record_island.py) uses unrelated toy Java source, not original game logic. Hosted GitHub CI cannot repeat these owner-private original-v311 comparisons. Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**. Continue larger renderer and tile dependency closure without claiming full game acceptance.
