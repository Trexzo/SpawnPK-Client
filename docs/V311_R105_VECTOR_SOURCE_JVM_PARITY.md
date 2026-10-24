# Original v311 R105 — audited renderer-vector source island

**Owner-private original authority:** v311 `client(20261021-111920).jar` SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Only redacted class/hash/count metadata is shared on GitHub. The reconstructed original-game Java, original client binary, emitted classfile binaries, private probes and vendor binaries remain **OFF PUBLIC GITHUB**.

## One genuinely new original-source class

| Original JVM class | Original class SHA-256 | Original-name Java9 rebuilt class SHA-256 | Fresh original ordered JVM instruction matches |
| --- | --- | --- | ---: |
| `rs/R.class` — mutable three-axis vector arithmetic/copy | `64043c3978c2efa31eab9d16dec7cb76b5a02fa9a1f6dc19603d2c3d0dafaba8` | `4b4d267f123ab108d96f99c3a39731af79c45e2e946fa1ad3c1e9d42968df5e1` | **159/159** |

Exact original declarations, field and method descriptors, ordered JVM opcodes, symbolic operands, instruction offsets and branch sites, together with the Java9 original string-concatenation bootstrap recipe, match a genuinely independent reconstruction. The source class has no unselected original-game static class dependencies. It is upstream of the renderer's still-unrecovered particle subsystem through `rs/r/c` and `rs/k/c/a`; this is **not** a new direct `rs/k/e` dependency resolution.

The original has `clone():Object` as a **synthetic JVM method** delegating to an obfuscated vector-copy method. A strictly scoped compiler-output-only transform changes exactly this one access flag from `ACC_PUBLIC` to `ACC_PUBLIC|ACC_SYNTHETIC`, validating classfile format/method identity and leaving executable Code unchanged. The original and rebuilt class match **159/159 exact original symbolic JVM instructions**, and reflection confirms the expected synthetic bridge shape. The complete source text, constant-pool binary layout, all classfile attributes and original binary byte identity are not claimed to match.

## 77-classfile source-generated build

The previously accepted R104 source island comprises **75 genuine reconstructed original Java type sources and one compiler-generated switch-table donor**. R105 adds one authentic original `rs/R.java` source, so a single `javac --release 9 -proc:none -g:none` invocation now generates **77 original-named classfiles / 7,984/7,984 matching original JVM instructions accounted for**. All **76/76 previously accepted R104 compiled classfile SHA-256 fingerprints are unchanged**. The previous **7,825 instructions retain R104 exact-parity certification through byte-identical rebuilt outputs**; the 159 genuinely new instructions were freshly compared. Zero temporary implementation stubs and zero missing explicit original project-class dependencies were found.

The compiler's only original-binary-derived dependencies are separately SHA-pinned, temporary **GNU Trove (1,595), Google (2,607) and LWJGL (967) vendor-only classfiles**, with **ZERO original `rs/` game classfiles** on its classpath. Existing reviewed compiler-only reversible class/package and vendor aliases are preserved. No vendor or game binaries are distributed in the private ZIP.

The headless isolated original-JAR-versus-rebuilt JVM probe produced **130/130 exact new behavior comparison matches**, including arithmetic with signed-int boundaries, floating-point NaN/infinities, copy identity and mutation, deterministic degenerate random ranges, string-concat formatting and reflective `clone()` synthetic metadata. Earlier R104 behavior cases were not rerun. This verifies bounded Java behavior, **not** actual OpenGL/game-runtime rendering or full particle-system correctness.

## Reproducibility and fail-closed evidence

Private source-only ZIP `SpawnPK-v311-R105-Vector-77-Class-Private-Sources.zip`, SHA256 **`bbd7f6d5389dfe016963c2d68fba7c734a3b05b45f9480ce37843508bfead167`**, was freshly clean-extracted and independently passed the entire private 77-class source/rebuilt-JVM/bootstrap/behavior verifier and **8/8 deliberate fail-closed cases**: modified Java source, missing source, incorrect original whole-JAR SHA, changed original vendor SHA, unreviewed compiler alias, modified compiler tool, modified clone-flag restoration tool, and changed actual JVM instructions refused **even after both candidate-source and rebuilt-class SHA fingerprints were repinned**.

The ZIP contains 77 original-game reconstructed source files, manifests and JDK-only probes/verification scripts, with **no original game JAR, emitted `.class`/`.jar` binaries, vendor library binaries, fonts, assets, account details or credentials**. It is owner-private and must not be uploaded to public GitHub.

## Distinct cumulative accounting and limits

Prior R104 accepted ledger: **104 distinct original-v311 classes / 9,021 original JVM instruction matches across separately verified builds**. Adding original `rs/R` (**one new distinct class / 159 original JVM instructions**) yields **R105: 105 distinct original classes / 9,180 matching original JVM instructions cumulatively across separate accepted builds**. The largest **single** source-generated island is **77 original-named classfiles / 7,984 instructions**; this is **not** a single 105-original-source compilation.

The [public synthetic-only Java9 clone-bridge test](../tests/test_v311_synthetic_clone_bridge_flags.py) verifies the generic copy-only metadata flag mechanism and refuses unrecognized targets using entirely unrelated toy Java source. Hosted CI has **no original game JAR** and cannot rerun the private original-v311 proof. Hosted results must be checked separately.

The large original `rs/k/e` renderer, `rs/a/a` scene model, related `rs/r/c` particle subsystem and seven provisional `rs/I`/tile classes remain unrecovered or incomplete. Neither a full 1,184-class original-source compilation nor original full binary byte equality, native/OpenGL correctness, game launch or authenticated gameplay has been proven. **Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) DRAFT and UNMERGED.**
