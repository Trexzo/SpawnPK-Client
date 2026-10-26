# Original v311 — Java2D color-tag text renderer source and bootstrap parity

**Evidence date:** 2026-10-22. User-owned original v311 client JAR remains private. Original uploaded `client(20261021-111920).jar` exact SHA-256: `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`.

## Newly recovered original source component

The actual v311 `rs/ui/components/x.class` is a Java2D rich-text painter implementing the previously recovered `rs/ui/components/w` rendering interface. It draws strings with a default color, supports inline `<col=...>` RGB markup and optional text shadows, stores point/font/color/text settings, returns pixel width/height and restores the caller's font when a custom font was used. It is **client UI-support code**, not the main world renderer or `rs/V` scene engine.

| Original/rebuild observation | Measured result |
|---|---|
| Original `rs/ui/components/x.class` SHA256 | `6b32db3ce607727208c975d98bf34c75ba8bbcf30670bebb88b4112d4901bc62` |
| Independently Java9-compiled `rs/ui/components/x.class` SHA256 | `62ad0d815d054a97208af48635e55e33ee949dc00ee73ae8f66cba180f001f4e` |
| Direct project dependency | `rs/ui/components/w.class` — originally `cca4907c0111fbe5de3f8e916c84cb38b9cc11ca75e759dc4a0905a13a3f0e1d` |
| JVM symbolic instruction/offset parity | **198/198 exact** |
| Real original-vs-rebuilt headless raster comparisons | **24/24 exact dimension and ARGB pixel SHA256 parity** |
| BootstrapMethods recipe parity | **exact same `StringConcatFactory.makeConcatWithConstants` target/recipe** |
| Private test log SHA256 | `e1868f18f1e53e2d7d9f38abcda4281c682ef7c59913e0c9080541fd7d72f023` |

The private reconstruction was compiled independently with `javac --release 9 -g:none -proc:none -encoding UTF-8`, **no original client binary on the classpath**, alongside a privately reconstructed copy of the already verified `rs/ui/components/w` interface. The original and rebuilt copies each have all **198 matching JVM instruction triples (offset, opcode, resolved operand/comment)** after normalizing numeric constant-pool indexes. The chosen Java lexical variable scope also preserves exact original local-variable reuse and branch offsets.

The original and source-built Java 9 classfile SHA256 hashes **differ**. This is not a claim of complete classfile byte identity, compiler provenance, original source syntax or all StackMapTable/attribute equality.

### Pixel behavior experiment

A JDK headless reflection probe loaded the **exact official original JAR** and the privately compiled source-built class into separate isolated classloaders, rendering each into a `260×64` ARGB `BufferedImage` using the same JDK and baseline `Dialog` font. For each case, it compared both returned `Dimension` values and SHA256 of **all 16,640 ARGB pixels in row-major order** (4-byte ARGB per pixel).

The 24 combinations covered six input strings (plain, a single six-digit RGB tag, multiple color tags including a three-digit tag, empty text, multiple six-digit tag changes and consecutive color tags), two shadow states and two font/background setups (default `Dialog` and an explicitly selected bold `Serif` font, including a filled background). **All 24/24 matched** on this machine. This remains an isolated JDK headless raster experiment; GPU rendering, Minecraft, SpawnPK login/server behavior, arbitrary HTML/markup syntax and cross-platform font raster identity are not proven.

### Public verifier vulnerability closed: invokedynamic bootstrap recipes

The pre-existing `standalone_source_parity.py` compared `javap -c -p -s -constants` declarations and ordered Code instructions. That can **falsely accept** a different Java 9 string-concatenation recipe: for example `Color.decode("#" + code)` versus `Color.decode("0x" + code)` can have identical invokedynamic instruction offsets and method descriptors but different bootstrap `makeConcatWithConstants` recipes, producing different output.

The verifier now invokes `javap -v -p` on **both exact original and source-built classes that contain `invokedynamic`**, and checks canonicalized `BootstrapMethods` entries, including method-handle targets and argument recipes. Only numeric CP slot indexes are normalized. Missing, ambiguous, changed or unreadable bootstrap data **fails closed**; an exact SHA-256 witness is recorded in accepted reports. This is not blanket verification of every JVM attribute, every Java invokedynamic runtime call site or semantic equivalence.

A new **synthetic-only** Java9 CI test independently compiles an unrelated small text-rendering interface and implementation, checks source/bytecode/bootstrap parity, renders three identical headless text-pixel cases, then deliberately alters a string prefix and requires rejection **even when `javap -c` instruction layouts match**. The proprietary v311 Java reconstruction and original client JAR were **not** added to GitHub CI or the public repository.

## Cumulative recovery scope

The preceding GitHub-documented milestone established **41 distinct** independently source-recompiled original v311 classes and **1,666** matching original instructions across multiple compilation records (not a 41-class single Java build). This newly verified original `rs/ui/components/x` component adds **one distinct class and 198 instructions**, yielding **42 distinct original classes / 1,864 matching original ordered JVM instructions** across **separate** private source compilation records. It does not mean a 42-class combined `javac` source island; previously verified source-island and class/package collision constraints remain in force.

The next meaningful source target is a further dependency-connected UI/scene-support class that uses this text painter or the earlier Java2D border renderer, with exact original class/member identity and independent bytecode/raster verification.
