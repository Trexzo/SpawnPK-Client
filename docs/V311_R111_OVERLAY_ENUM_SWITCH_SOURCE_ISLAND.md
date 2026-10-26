# Original v311 R111 — five-class overlay enum and synthetic-switch source island

**Evidence date:** 2026-10-24. The owner-provided original v311 JAR is pinned by whole-JAR SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The original game JAR, recovered Java sources, compiled original game classfiles and owner-private verification probes **remain off public GitHub**.

## Five genuinely distinct original-v311 JVM classes

| Original JVM class | Original class SHA-256 | Privately source-generated and inverse-restored class SHA-256 | Exact original JVM instructions |
| --- | --- | --- | ---: |
| `rs/l/f/l.class` — ten-position overlay enum | `5d8c2fe0a05ba40d2c2b604f366bbd023166955f36a89b556072ef4d5272f280` | `f66695cfe0a9a3348f440771f13f1046bb266cd39fd057262138efdd0519838c` | **120/120** |
| `rs/l/f/d.class` — generated seven-case overlay switch table | `47b71a8d387d44abb870b15bf0146ae6799cb9d5f3d4947074c842e40b2f7d88` | `ddd4bb66c68331f8bb37ebad0f5892f8317c62cbdbaaa09fc05190c2b4ef434d` | **54/54** |
| `rs/l/f/h.class` — generated three-case switch table | `5fd63e51c1cab94c07589bd9fd0be51011b19911bdd90ee8d87ca6effb45e627` | `801a3ed86b883968ed06db021a6fa5f6bf3d29166b39f0fdfb45f60a31291748` | **26/26** |
| `rs/l/f/k.class` — generated two-case switch table | `969c3351f67f63e8e387c0595e06ad28b3def129d5b18039921057e0cca92a4f` | `72b8823759839c068a846eacc4588b110cd6daad12dd32b5e38cb529d658e852` | **19/19** |
| `rs/l/f/n.class` — generated seven-case switch table | `2378d2dd7cb6c1cfad5c3293a6d9e3c3cfedef71011906ca9b0103ee123e7368` | `602209c182361c22ccdc6f8a569eebcfd8cceebeeb3fd4c66a27b156d33224cf` | **54/54** |
| **New exact original JVM matches** | | | **5 original classes / 273 instructions** |

These five names are not among the 106 distinct classes already accepted in R106's cumulative inventory. The new private source island **does not compile into or extend R106's 78-class group**. It consists of one genuine source enum declaration and four source donors with Java `switch` statements that each generate one *synthetic* enum-switch JVM helper. The four donor owner classes are discarded, leaving exactly five canonical original JVM class identities. Do **not** interpret the result as five ordinary original-authored Java type declarations.

### Original bytecode and behavior evidence

The private verifier checks SHA pins for all five owner-original classfiles, all five Java sources, all five inverse-restored classfiles, all tools/probe, and the full original JAR. It compiles with **Java9 `javac --release 9 -proc:none -g:none`**, with an empty original game and third-party compiler classpath. Exact original-vs-source-generated `javap -p -s -c` comparison preserves all **273/273 ordered JVM instructions, declarations, exact instruction offsets, branch targets, symbolic field/method operands and synthetic switch exception-table rows**, normalizing only numeric constant-pool indexes.

For the enum, a reviewed copy-only classfile member-name transformation restores obfuscated static enum fields and compiler-created members *without changing the actual runtime `Enum.name()` values*. Four reviewed switch-map identity transformations restore each compiler-generated synthetic class/field/member reference and remove only the unneeded donor `EnclosingMethod` metadata in copied outputs; JVM `Code` and catch-handler instructions are not modified.

The owner-original-vs-rebuilt isolated JVM probe matched **65/65 behavior cases**: all ten enum names/ordinals, all ten original obfuscated field identities, clone identity for values(), all 40 source-order-sensitive switch-map slots, and synthetic class/constructor/method reflection shapes. **Static explicit project-class dependency closure is complete for this selected five-class island**, with zero unselected project dependencies, no source stubs and no original game binaries on the compiler classpath. This does not prove runtime graphical rendering, game integration or full original classfile byte identity.

### Independent clean replay and deliberately invalid cases

Owner-private source/verifier ZIP: `SpawnPK-v311-R111-Overlay-5-Class-Private-Sources.zip`, SHA256 **`59c1d125c0a40503c1f61243d40474664aff00d94922d0b94206213b7615d095`**. Its 14 files include exactly five original source inputs (one enum and four donor source files), a probe, manifests, compiler/identity tools and refusal tests. **NO original game JAR, `.class` or `.jar` binaries, vendor binary libraries, credentials or game assets.** The reconstructed source ZIP is owner-private and **is not uploaded to the public GitHub repository**.

The ZIP was **independently clean-extracted**, then replayed against the same exact private owner-original JAR. Source/compiled SHA checks, Java9 rebuild, original symbolic JVM match and all 65 behavior cases passed. **Seven of seven deliberate invalid inputs were correctly refused**: tampered source SHA, missing source, incorrect original JAR hash, modified switch-identity transformer, modified enum transformer, extra source stub and changed switch case *ordering* after explicitly updating both donor-source and emitted-class SHA pins. The last case still fails exact original JVM bytecode comparison. Merely changing a switch-case return value would only affect the discarded donor owner class; R111 negative tests deliberately avoid that false-positive coverage.

### Accurate cumulative count and scope

The prior accepted R106 original-source cumulative ledger was **106 distinct recovered original classes / 9,521 original matching JVM instructions across separately accepted source builds**. This five-class separate island adds exactly **5/273**, giving **R111: 111 distinct accepted original classes / 9,794 matching instructions cumulatively across separate source builds**.

The previously verified largest **single** source-generated source island remains **R106: 78 classfiles / 8,325 matching instructions**; R111's additional group is separately built and has five outputs. **There is no one-shot 111-source build or complete v311 client.**

[Public independent synthetic-only 10-position enum and four generated switch-table regression](../tests/test_v311_synthetic_overlay_switch_island.py) uses unrelated toy Java sources, checks generated class repeatability, runtime mappings and mutation of genuine generated switch JVM code. Hosted CI cannot repeat the owner-private original-v311 comparisons and must be checked separately.

The original `rs/k/e` renderer, `rs/a/a` scene model, seven provisional scene/tile classes and full 1,184-class source graph remain unrecovered. Original complete-classfile attribute identity, game renderer/OpenGL behavior, native/resources closure and live gameplay have **not been tested**.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**.
