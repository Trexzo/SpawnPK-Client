# Original SpawnPK v311 R116 — renderer/scene dependency source islands

**Private original authority:** SHA-pinned owner-v311 client JAR `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The owner-provided original JAR, recovered Java source, compiled game/vendor classes and private behavioral verifier are **not uploaded to GitHub**.

## Two NEW, distinct original-v311 classes with exact symbolic Java9 JVM instruction parity

| Original JVM class | Role | Original class SHA256 | Independently rebuilt SHA256 | Ordered JVM instruction parity |
| --- | --- | --- | --- | ---: |
| `rs/k/e$a` | Three-valued NONE/OPENGL/OPENCL renderer mode enum, the original `rs/k/e` renderer's direct nested dependency | `b5ee5ed752fdcbfd389f40b9457141db371dc58db371327054aa2de1654d5b22` | `6684d96ae9e3c97983a44ff20fb6d055a1a50c858ca9eedf7393d884a09445ff` | **50/50** |
| `rs/a` | Doubly linked scene-node base directly referenced by blocked `rs/a/a` scene model | `7c33983b6e49dc2cd8b4b5bde2bd0550a4977c1eaa483025630b5c16105e735f` | `cabc38cf4fe192004fdfebd164de22ae846bcdb32ed468534c87f8166ac77e1a` | **24/24** |
| **R116 new** | | | | **2 / 74** |

The scene island independently compiles **two classfiles: new `rs/a` plus previously accepted `rs/t`**, the latter freshly verified **24/24 original JVM instructions** (original SHA `430c61233ef1d46a3dadbe4947a3d4d17019db2bc1d4678dc732623ea1b3274f`, rebuilt SHA `334fb23b8bf2ad12c1ef03d8e881c39d5cceda51e03a830c057bd6980799bb54`). The already accepted `rs/t` is *not* counted again as a new class or new cumulative instructions.

The renderer island compiles a minimal **Java9 nested-enum donor** `rs.k.e { enum a { ... } }`: only the original-named generated nested enum `rs/k/e$a.class` is selected. The temporary synthetic **`rs/k/e.class` owner output is discarded** and never represented as the recovered full renderer. Enum obfuscated constant field names, generated values-field and helper identities are restored on a *copy* of compiler output without edits to JVM `Code` or exception handlers. Do **not** call this an authentic restored `rs/k/e` implementation. There is no one-shot 116-class source compilation and no complete classfile binary-identity claim.

Both selected source islands build with `javac --release 9 -g:none -proc:none`, an empty compiler classpath/sourcepath apart from explicitly passed recovered Java source, **ZERO original game/vendor compiler binaries and ZERO unreviewed source stubs**. Private `javap -p -s -c` comparison confirms original field/method declarations, symbolic operands, byte offsets, branch targets and ordered JVM instructions. Numeric constant-pool indices only are normalized.

### Private runtime limitations and evidence

The `rs/k/e$a` `InnerClasses` attribute refers to the *unrecovered* outer `rs/k/e`. Invalid-value reflection behavior requires the real outer class metadata at runtime. Therefore the **17/17 original-vs-rebuilt Java reflection/node-unlink observations** are checked using the reconstructed scene+enum classfiles *first* and the SHA-pinned original JAR as a **trailing runtime-only fallback**. The original owner JAR is NEVER on any `javac` compiler classpath. This is evidence for these specific behaviors with an original outer-class runtime fallback, **not isolated full renderer runtime closure**.

The private archive `SpawnPK-v311-R116-Renderer-Scene-2-Class-Private-Sources.zip` is SHA256 **`c103537bdaa388d1bf12bf06b252b286c4382d3e689c68f006dd61f4083c61c7`**. It contains source, manifests, probes, and verifier, **not** the original JAR, compiled classfiles, vendor binaries, game assets or credentials; it remains owner-private. Complete independently fresh-extracted verification: original JAR pin and class pins, source/probe/tool hashes, compiler output identities, 50+24 newly matching exact JVM instructions plus 24 already accepted `rs/t` instructions, **17/17 behavior observations**, and **8/8 deliberate fail-closed refusals**. Invalid cases include source/probe/metadata tampering, missing source, unreviewed fake source, wrong JAR hash, *repinned enum ordering mutation*, and *repinned node algorithm mutation*; altered JVM code is rejected despite refreshing both source and compiled class SHA pins.

The [public regression](../tests/test_v311_synthetic_renderer_scene_dependency_islands.py) consists entirely of unrelated toy Java9 types with no recovered game source and no original JAR. It checks nested enum donor output isolation, repeatable output and actual generated JVM mutation detection after rehashing. Hosted CI only certifies this independent synthetic safety fixture, not private original bytecode parity.

### Cumulative accounting / remaining blockers

R114 previous accepted baseline: **114 distinct original v311 class identities / 9,964 cumulative matching original JVM instructions** across multiple independently certified source builds. New R116: **2 new identities / 74 newly matched instructions**, yielding **116 distinct original classes / 10,038 cumulative matching JVM instructions, across SEPARATE source islands**. The largest single integrated source-generated group **remains R106: 78 original-named classfiles / 8,325 original matching instructions**.

The direct-dependency audit consequently increases to **17/36** for original `rs/k/e` renderer and **5/14** for original `rs/a/a` scene model, based on distinct accepted classes, **not** closed parent source groups. `rs/a` also collides with Java package `rs.a.*`; future integrated-source build needs a reviewed reversible compile-time alias, not a fabricated stub. The renderer `rs/k/e`, scene-model `rs/a/a`, seven provisional scene/tile classes and whole-client/graphics/native/gameplay integration remain unaccepted.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**. No manual gameplay acceptance test required for this source-only milestone.
