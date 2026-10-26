# Original SpawnPK v311 — UI border renderer source parity

**Audit date:** 21 October 2026. This is evidence from the exact uploaded original `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Original JAR, reconstructed Java, original game binaries and private Java behavior probes were not committed to this public GitHub repository.

## One new genuine original v311 source reconstruction

The new original client `rs/ui/components/a.class` implements a Java2D/AWT border drawing component. Its direct original `rs/` class dependencies are **only** `rs/ui/components/d.class` (the previously source-rebuilt UI color theme) and `rs/ui/components/w.class` (the previously source-rebuilt UI drawing interface). The strict updated classfile scanner verifies both dependencies.

| Verified original v311 class | Original SHA-256 | Independently rebuilt SHA-256 | Ordered original JVM instructions |
|---|---|---|---:|
| `rs/ui/components/a.class` | `e4e6e9e0c62bc0619130fe4242fbdf50f70a426b68634a2ead8bb1b1473d2c6e` | `8ea653d85fd1660327cfe4d3eb2fd03ae5a9a7df8db49b989956cc3b55306292` | **209/209** |
| `rs/ui/components/d.class` (previously verified) | `32a04540699c5e0a9625dfe3e59c4cfa79af50117879b07d754c572cfcc40919` | `bffd73db53c7f140444ce4806a92ba3836d038ca6e54b9b4a0e89737f924df5e` | **12/12** |
| `rs/ui/components/w.class` (previously verified) | `cca4907c0111fbe5de3f8e916c84cb38b9cc11ca75e759dc4a0905a13a3f0e1d` | `a574bab10a5c7adf2a062d512c9c81acb683789830c2b55d7ac88bb10493e8d2` | **0/0 (interface declarations)** |
| **Three-class UI island** | | | **221/221**, declaration and ConstantValue parity |

The three canonical-name Java sources were compiled independently in one Java 9-target `javac --release 9 -proc:none -g:none` invocation with an **empty original-game binary classpath and external sourcepath**, producing exactly three matching JVM class names. Original-vs-recompiled `javap -c -p -s -constants` compares ordered opcodes, byte offsets, branch targets, resolved members, interfaces, fields, constructors and static-final constants. The symbolic instructions/fields/constants match after numeric constant-pool slot normalization. The original and built full classfile SHA-256s **differ**; byte-identical full classfile attributes, StackMapTable or general game behavior are not claimed.

The cumulative exact original-v311 recovery records now contain **41 distinct independently source-recompiled classes and 1,666 matching original JVM instructions**, accumulated across **separate verified source-build islands**. The largest previous single combined original-v311 build remains the separately attested **35-class** source island. This new three-class UI island is not evidence of a single 41-class compile or complete 1,184-class source tree.

## Original versus independently rebuilt headless pixel behavior

A separate private JDK-only harness loaded the exact original client JAR and independent three-class rebuilt UI output using isolated classloaders, invoked `rs/ui/components/a` with a fresh 32×32 `BufferedImage`, and compared **all ARGB pixel values** via SHA-256. Four bounded combinations of default/setter constructor flow and explicit color/rectangle constructor flow, each with background fill enabled or disabled, matched exactly:

| Scenario | Size returned | Original/rebuilt 32×32 pixel SHA-256 |
|---|---|---|
| Setters, fill off | 16×14 | `81d3256601677214db18ec159ea1f3bbe74c4f6b2cfcdb1295a0da71cf311fad` |
| Setters, fill on | 16×14 | `d21fb5e4d9856e96bc5a8bccf321dbe7fe47b38afe4afdcc8831a98791a80150` |
| Three-arg constructor, fill off | 15×12 | `a04902f90874dd10a8b1a6744220cb2ea359728a4dd04cf8e7fd849e7026641a` |
| Three-arg constructor, fill on | 15×12 | `bc392868c31add3bfc255aa0153d1828342b9dcece4392a40f6b527387fde98f` |

These four comparisons exercise original-vs-rebuilt AWT drawing behavior **in headless Java**, not Minecraft/SpawnPK game rendering, server operation or general UI device compatibility. The exact original JAR was read-only and no account was accessed.

## Hosted CI and corrected dependency frontier

`tests/test_v311_ui_border_source_parity.py` separately compiles three **unrelated synthetic Java9 source classes** (UI interface, color theme, concrete renderer), verifies original-name JVM parity without client binary classpath, checks the two original-format declaration/class references are inside the selected synthetic source set and verifies a deterministic headless pixel raster via two independently loaded outputs. Public hosted CI **cannot replay the private original-v311 pixel evidence**.

The preceding [declaration-complete source dependency audit](V311_DECLARATION_DEPENDENCY_CLOSURE_AUDIT.md) is essential: its corrected field/method/Signature scanner rejects falsely closed source frontiers such as original `rs/n` and `rs/M`. A fresh **40-class existing selection** still contains no missing explicit project references under the corrected scanner; adding the UI renderer requires and supplies `rs/ui/components/d` and `rs/ui/components/w`.

## Limitations and next target

The complete original v311 scene class `rs/V` and tile class `rs/H` remain **not** source-recovered. Their public role/metadata evidence is only structural. The next source recovery work should target additional dependency-closed UI-support classes or substantive scene dependencies, preserving exact original class/member lineage and avoiding accidental promotion from source similarity alone.

No original JAR, private candidate Java, generated game classfiles, source manifest or private harness is distributed by this report.
