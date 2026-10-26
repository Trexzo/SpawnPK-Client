# Original v311 R67 — 38-class geometry/scene source recovery with reviewed class/package alias

**Evidence date:** 2026-10-23. Original authority is user-provided v311 `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The original game JAR, independently reconstructed proprietary Java and generated game classfiles are **not** committed to GitHub.

## Three authentic new source-rebuilt original classes

| Original class | Original SHA-256 | Independently compiled/restored SHA-256 | Ordered original JVM instructions |
| --- | --- | --- | ---: |
| `rs/k/c/b.class` — 216+72 packed coordinate/index buffer | `029571ee0e93fea422000e1971cc280e665b361c5904454e9329a12b97681752` | `8a906ccfe80bf36cb64ecf4a84b7397f122fffbdc0bc2a80f29151939b03e3be` | **633/633** |
| `rs/a/i.class` — scene six-int record and six accessors | `55ade972e312ae8402cc5855248b087d67753d7b8b24923955619bca7733688a` | `8a364bd28b161204480498777a5217f2754611ebf740904bfb889de2f1c911ae` | **39/39** |
| `rs/runelite/a/a.class` — scene-record interface | `d4769d3495be887b716f3f0d0ee816d159f8c5cd46f640a0bd6759e59f2ac43d` | `a4d3d382f2676fd8ddb2d19cb194cbbe07717a15fd714c28de6d36e81363fc25` | **0 (six abstract method declarations/descriptors match exactly)** |
| **Newly accepted** | | | **3 classes / 672 exact original JVM instructions** |

The zero-instruction interface counts as a source-recovered class ONLY because all six declared method JVM descriptors and the interface declaration match the original; an empty Code comparison by itself would be insufficient.

## Real class/package naming collision — narrowly bounded, reversible resolution

The original JVM includes **both** `rs/k/c.class` (Java class `rs.k.c`) and `rs/k/c/b.class` (Java class `rs.k.c.b`, under Java package `rs.k.c`). They are legal as JVM classfile names but **cannot both be compiled together as unchanged Java source names**.

The private source verifier uses a reviewed, disposable same-package **compile-only alias**: the owning `rs/k/c.java` class declaration and constructor are staged as `rs/k/RecoveredFloatBufferV311.java`, while the 37 other canonical Java source files are not modified. Original `rs/k/c` JVM identity is restored in **copied compiled classfile constant-pool metadata** before bytecode comparison. The alias is **not** a semantic rename and does not modify the private canonical source or original JAR. Every previously accepted original classfile SHA is preserved **after inverse classfile identity restoration**, including the aliased `rs/k/c` class. A deliberate changed alias declaration is rejected even if its source hash is updated.

One independent `javac --release 9 -proc:none -g:none` execution compiles **38 authentic original Java source reconstructions** (35 previously accepted R64 sources + three new classes), with **zero original client/game binary classpath or sourcepath dependency**. The complete 38-class copied inverse-restored set has **3,923/3,923 original JVM instructions, exact declarations/byte offsets/branch targets/symbolic operands**, **35/35 unchanged previously accepted rebuilt class hashes**, **zero temporary source stubs**, and **zero missing explicit project-class references** under the original constant-pool/descriptor scan.

Original-versus-source-built isolated-JDK behavior transcript comparisons match **21/21 new full-array SHA256 geometry/record/interface cases**, plus previously accepted **36/36 scene/GUI**, **39/39 matrix**, **22/22 direct-buffer** cases, total **118/118**. The new 21 lines cover 216-entry and 72-entry full geometry index arrays with six diverse parameter sets (including integer boundaries), eight six-field record scenarios, and the exact declared interface shape. Five deliberate fail-closed private tests reject: direct source SHA mutation, altered bytecode despite repinning source/built SHA, missing Java source, unauthorized alias modification, and wrong original whole-JAR SHA.

**Certified cumulative tally:** previous accepted **64 unique classes / 4,459 exact original JVM instruction matches** across separate source-build records, plus **3 / 672**, resulting in **67 distinct original-v311 source-built classes / 5,131 matching original instructions** across separate independent builds. **The largest single, presently dependency-closed source compilation is 38 original classes / 3,923 instructions, not all 67 classes together.** Source closure is static original JVM metadata closure, not reflection, dynamic classloading, assets/native/OpenGL, server or gameplay verification. Neither full complete classfile SHA/binary identity nor complete original-v311 client source recovery is claimed.

Owner-only private ZIP: `SpawnPK-v311-R67-Scene-Geometry-38-Class-Private-Sources.zip`, SHA-256 `b1d54a8c7747a69556a73e4502cffb30b88e5fa875a5e5fda6b46122bc47910d`. ZIP was independently re-extracted and its full verifier and five negative tests passed. It contains 38 reconstructed Java files, private verifier, original SHA evidence, behavior probes and clear alias protocol; **NO original JAR, compiled game classfiles, game assets or account data**. It must not be pushed to this public repository.

The [synthetic Java9 alias/geometry regression](../tests/test_v311_synthetic_geometry_alias_closure.py) uses only independently authored toy JDK classes and tests the class/package shadow plus exact inverse alias restoration and fail-closed mutation. Hosted CI has no access to original private game data and must be certified independently.

The original `rs/I` and six tile candidates remain **provisional and excluded** from the accepted cumulative total: the original `rs/k/e` renderer and `rs/a/a` model-source chains are still unavailable in source. PR #1142 remains **DRAFT, UNMERGED**. No manual gameplay test is required at this source-only checkpoint.
