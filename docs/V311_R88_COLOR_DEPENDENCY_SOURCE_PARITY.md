# Original v311 R88 — 59-source renderer/model color dependency

**Owner-private original authority:** `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Neither the original game JAR, private recovered Java sources, reconstructed game classfiles, nor real original-vs-rebuilt JVM probes are publicly hosted.

## One new, independently recovered class on both blocked dependency frontiers

The original `rs/l/f.class` is a short/int color packing and conversion utility referenced by the still-unrecovered original renderer `rs/k/e` and scene model `rs/a/a`. This R88 recovery replaces neither of those larger classes. It has **no original project-class dependencies outside itself** under the constant-pool/descriptor scan.

| Original class | Original class SHA-256 | Independent Java9 rebuilt SHA-256 | Exact original JVM instructions |
| --- | --- | --- | ---: |
| `rs/l/f.class` | `bb475f0e99bb3f852e1d028f7026acf36cad570954e5e2bfd76bd25023ec6c9f` | `90817286488dbebf09fbcdf948583c9753fa52c76d6da4759d4b4e5220ffa1d1` | **295/295** |

The independently compiled source reproduces all original class and member declarations/JVM descriptors, 295 ordered JVM opcodes and **exact original byte offsets, branches and resolved symbolic operands**, normalizing only numeric constant-pool indexes. A separate `javap -p -constants` comparison matches the original constant-value fields (63, 7 and 127). Original complete classfile bytes/attributes, original authored source-text identity and all external graphics/game behavior are not claimed.

## 59 genuine source classes in one closed Java9 build

R87 certified **58 original-name source classes and 5,913 matching original instructions**. The extra `rs/l/f` source compiled **in one `javac --release 9 -proc:none -g:none` invocation** with all 58 old sources and an explicitly empty original-game compiler classpath/sourcepath. The existing strictly reviewed `rs/k/c` class/package compile-only alias was reversed in **copied** compiler outputs before testing. This leaves canonical owner-private Java and original JAR unmodified.

The clean-extracted R88 verifier independently checked all 59 original/source/rebuilt SHA pins, **58/58 unchanged previously verified compiled class SHA fingerprints**, full static original-project dependency closure, exactly 59 emitted original-name Java9 classfiles, zero temporary declaration-only stubs, and **295/295 freshly compared exact symbolic JVM instructions** for `rs/l/f`.

The source-closed combined build accounts for **6,208/6,208 original JVM instructions**: R87's 5,913 previously certified instructions retained by identical rebuilt class SHA values plus the 295 newly compared instructions. It does **not** pretend the prior 58 original class disassemblies were all rerun in this faster verification.

## Bounded JVM behavior and refusal checks

New headless JDK original-versus-rebuilt color/bit-packing and RGB/HSB/gamma conversion trials matched **204/204 output cases**, including integer sign/boundary values, masks, formatting and unusual floating-point inputs. Previously certified R87 behavior cases **were not rerun** and are not added to 204.

The source archive was **freshly re-extracted** and passed the complete R88 verifier, then **all five deliberate fail-closed negative trials from the extracted archive**:

1. Changed source SHA rejected.
2. Missing original-name source rejected.
3. Wrong whole-original-JAR SHA rejected.
4. Unauthorized alias mapping rejected.
5. Altered real original-name JVM instructions **rejected even after repinning both reconstructed-source SHA and emitted-class SHA**.

Owner-private archive: `SpawnPK-v311-R88-Color-59-Class-Private-Sources.zip`, SHA-256 **`9264895e7ccd2bd8dbaa47344258f4ce0bd38338cd1e7d826c45d4a75ed5b304`**. It contains 59 owner-private Java source files, original/source/rebuilt SHA manifests, JDK behavior probe, standalone verifier, README and negative tests, **no original client JAR, compiled game classfiles, native assets, accounts or credentials**. It is intentionally **NOT committed to the public repository**.

## Correct distinct counts and remaining limitations

Previous accepted R87 cumulative: **87 distinct original classes / 7,121 original JVM instruction matches across separately certified source builds**. R88 adds only `rs/l/f` (**1 distinct class / 295 instructions**), resulting in **88 distinct accepted classes / 7,416 matching original instructions cumulatively**. The largest *single* independently source-closed compilation is **59 classes / 6,208 instructions**, **not** all 88 classes compiled together.

The seven provisional `rs/I` and tile sources remain **excluded**, because the substantially larger `rs/k/e` renderer and `rs/a/a` scene-model source chains are still unresolved. Recovering their shared leaf utility `rs/l/f` reduces the dependency frontier but does **not** promote those classes. Neither full 1,184-class client, classfile binary equality, reflection/native/assets/OpenGL nor authenticated gameplay is established.

The [public synthetic-only Java9 color parity regression](../tests/test_v311_synthetic_color_dependency_source_parity.py) tests unrelated toy Java, not recovered original game source. Public hosted CI cannot repeat the owner-private original-JAR comparisons. Keep [draft PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**.
