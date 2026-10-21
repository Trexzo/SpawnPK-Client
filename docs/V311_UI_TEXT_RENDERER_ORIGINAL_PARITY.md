# Original SpawnPK v311 — UI text renderer independently rebuilt with exact JVM and pixels

**2026-10-21.** This evidence was obtained directly against the user-uploaded original official v311 client `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The original JAR, reconstructed proprietary Java source, compiled classfiles and reflection harness remain private and were **not** uploaded to this public repository.

## Actual UI renderer source recovery

The previously identified dependency-closed candidate `rs/ui/components/x.class` implements the already recovered `rs/ui/components/w` interface. It is an original Swing/AWT text renderer with inline `<col=...>` color tags, shadow/outline drawing modes, custom fonts and text measurement. A complete Java 9 source candidate was reconstructed privately and compiled with **only the matching independently reconstructed interface source** — no original game class/JAR on the compilation classpath.

| Original class | Original class SHA-256 | Private source-built class SHA-256 | Exact ordered JVM instruction parity |
|---|---|---|---:|
| `rs/ui/components/x.class` | `6b32db3ce607727208c975d98bf34c75ba8bbcf30670bebb88b4112d4901bc62` | `62ad0d815d054a97208af48635e55e33ee949dc00ee73ae8f66cba180f001f4e` | **198/198** |
| `rs/ui/components/w.class` (previously verified) | `cca4907c0111fbe5de3f8e916c84cb38b9cc11ca75e759dc4a0905a13a3f0e1d` | `a574bab10a5c7adf2a062d512c9c81acb683789830c2b55d7ac88bb10493e8d2` | **0/0**, interface declarations match |

Original versus independently compiled `javap -c -p -s` matches all class/method/field declarations, JVM descriptors, ordered instructions, offsets, branch targets and resolved symbolic operands, after normalizing only numeric constant-pool indices and their formatting. Both compiled classes target Java 9 bytecode. The recompiled class SHA values are **not equal** to original classfile SHAs; no full StackMapTable/attributes or original-source provenance is claimed.

### A source-shape obstacle that was resolved

The original `a(Graphics2D)` method uses local-variable slot 8 both for the trailing color-free text segment and, after that segment's lifetime, for the measured font height. The first source reconstruction kept the segment in an outer lexical scope, so `javac` emitted a height `istore 9` and later `iload 9` despite having the same **198** JVM instruction count. Giving the segment a narrower lexical block allowed slot 8 to be reused, recovering the exact original `istore 8` / `iload 8` offsets and complete symbolic bytecode parity. Thus parity requires original compiler-compatible local-variable lifetime, not just behavior or count.

## Original versus rebuilt headless AWT pixels

A JDK-only `-Djava.awt.headless=true` probe loaded the exact original class and source-recompiled class in isolated `URLClassLoader` instances, supplied identical text with a hex-color tag, coordinates, color, font and graphics image, and compared returned `Dimension`, restored original font and **SHA-256 of the complete ARGB `BufferedImage` pixels**. Results were identical across all four combinations of outline and font override:

| Outline | Custom font | Dimension | Exact ARGB pixel SHA-256 (same original and rebuilt) |
|---|---|---|---|
| off | off | 72×20 | `0851b5d21c5ba3610f4dcafa2b5f9ecc41c4448870cad0d1c00a4d5db716103d` |
| off | on | 87×23 | `4e156f1548ce92932cb4b6df2deff481512cf6e89a5ac8b55fa525b7f681d92c` |
| on | off | 72×20 | `a7743a5364238b239a22f149894288568549cb1d58ce64dfd4af6e4e7cb69bdc` |
| on | on | 87×23 | `a54ad2b5becd834fd66cdaba9394aad26b37e8ba1e63eaf9a35f17378f016ded` |

These are **four actual original-client-vs-rebuilt graphics comparisons**, stronger than isolated field inspection but only for this bounded headless JDK/AWT environment. They do not prove actual live-client GUI performance, all font platforms, GL rendering, game/server behavior or every input combination.

## GitHub safety regression

A new synthetic `test_javac_local_variable_slot_scope_diagnostic` regression in `tests/test_v311_source_parity_diagnostic.py` checks a source-level lexical-block lifetime difference that changes javac local-slot opcodes even when the instruction count stays equal. The new general first-parity-difference diagnostic reports the first differing JVM offset/opcode without disclosing proprietary operands. Hosted GitHub CI only compiles synthetic Java examples; the user's actual v311 renderer source and pixel images are not published.

**Recovery accounting:** the [35-class fully compiled private source island](V311_THIRTYFIVE_CONNECTED_SOURCE_ISLAND.md) remains the last completed larger combined build, with **1,059/1,059** original instructions. Separately, [`rs/y/a` timer](V311_TIMER_BRANCH_PARITY_RECOVERED.md) is independently recompiled and matches **35/35**, and this `rs/ui/components/x` matches **198/198**. Therefore **37 distinct original project classes have source-to-instruction proof in these records**, totaling **1,292 verified original JVM instructions across individually compiled sources**. **A combined 37-class source-island build has NOT been run and must not be claimed.** Complete v311 source compilation remains far from achieved (1,184 original `rs/` classfiles).

Next milestone should merge both independently verified candidates into an exact-SHA-pinned private dependency-closed source-island build, then expand the original scene/client-rendering classes with the same bytecode and runtime boundaries.
