# SpawnPK original v311 R114 — 3-class enum source island

**Owner-original reference:** SHA-pinned v311 JAR `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The original game JAR, reconstructed private Java sources, compiled game/vendor binaries and account material are **not in this repository**.

## Three new distinct JVM class identities

| Original class (role) | Original class SHA-256 | Owner-private rebuilt class SHA-256 | Exact JVM instructions |
| --- | --- | --- | ---: |
| `rs/l/f/a/a/e` (expanding/showing state enum) | `e90df3799de55f939effd20541a9fec6687d472bbc31c712c55406e428203713` | `ed0fd12131f563fcbf68c2db75b584af27034a057728b4d0ceb702c04e548829` | **50/50** |
| `rs/l/f/a/f/b` (left/right positioning enum) | `45ff4c449b1fcc83f92a511e706730b5d47637cc68c654a555cbfc44f53a1109` | `57736fa828129010fca85ec3bd3e04a0790e68d18908e3211cc67099dc72db04` | **40/40** |
| `rs/l/f/a/i/g` (six-category UI enum) | `5618c2048476b2a4057995f1a47a2101a9f07b009636548d8336a281cb7e8260` | `6b8d3080b88475825ddf2f5ded8bb836b20e273b847ac65eb9cf3bd4a553b3fc` | **80/80** |
| **Newly accepted R114** | | | **3 original classes / 170 instructions** |

Each class is generated from an owner-private Java9 enum source declaration. A reviewed reversible post-compiler *metadata-only* transformation restores the obfuscated enum constant-field identities, generated values field and synthetic helper method. The transformation does **not edit executable JVM Code or exception handlers**. Full original-classfile binary identity and exact original authored-source text are not claimed.

## Private source and original binary verification

- A **single separate three-class Java9 compilation** produces exactly those three original-named outputs, without extra compiler outputs, using empty original game and third-party binary compiler classpaths.
- Selected explicit original-project constant-pool dependency closure: **zero missing**, **zero fake implementation stubs**.
- The SHA-pinned owner-original versus independently source-generated `javap -p -s -c` comparisons exactly match **170/170 JVM instructions**, declaration shape, exact instruction offsets, branch targets and symbolic method/field operands (numeric constant-pool indexes are normalized only).
- Original-JAR versus rebuilt-JDK headless enum reflection probe matches **20/20 output observations** for all enum names/ordinals, obfuscated original static constant identities, `valueOf`, `values()` cloning and invalid-value handling. **No graphics/UI gameplay execution was performed.**
- Owner-private source/verifier ZIP, `SpawnPK-v311-R114-Three-Enums-3-Class-Private-Sources.zip`, SHA256 **`f7319746d9601a06ca7cf921fab5e7f03014c2df8d28b89539378f2f023e59a2`**, was **freshly extracted and independently replayed** with the owner-original v311 JAR. It contains only 3 Java sources, manifest, compiler metadata restorer, symbolic verifier, probe, tests and README. **No original client JAR, `.class` files, vendor libraries, game assets or credentials**; archive is **not uploaded publicly**.
- The clean-extracted fail-closed suite rejected **7/7 invalid cases**: edited source, missing source, wrong original authority, unexpected extra source, tampered probe, tampered metadata transformation and altered original enum ordering **with both source and rebuilt fingerprints deliberately repinned**. The final case was still rejected by actual original-vs-built instruction comparison.

The [public synthetic-only three-enum regression](../tests/test_v311_synthetic_enum_family_island.py) uses **completely independent invented toy Java types**, tests Java9 compiler isolation/repeatability and compares actual generated JVM code after a repinned source/compiled-class order mutation. It has **no access to the private original game**, therefore successful public CI is a separate safety signal, **not original v311 parity certification**.

## Cumulative acceptance accounting

- Previous accepted R111 cumulative: **111 distinct original classes / 9,794 JVM instructions**, across separately verified source-build islands.
- New R114 contribution: **3 distinct classes / 170 matching instructions**.
- **R114 accepted cumulative: 114 distinct original classes / 9,964 matching instructions across SEPARATE source builds.**
- **Largest one-shot original-named source-generated build remains R106 at 78 classfiles / 8,325 instructions**. R114 is a **separate three-output source island**. There is **no one-shot 114-class build** and R106/R111 behavior probes were not rerun as part of this new island.
- Large original `rs/k/e` renderer and `rs/a/a` scene model, seven provisional scene/tile sources, all native OpenGL/graphics and whole-client runtime acceptance remain **unrecovered/unproven**.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED** until an appropriately scoped integration and original-owner runtime certification exists.
