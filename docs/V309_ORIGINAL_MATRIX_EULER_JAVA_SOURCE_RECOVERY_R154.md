# R154 — original-v309 matrix Euler-angle Java source reconstruction

Original client-only source recovery, stacked on [R153 #1040](https://github.com/Trexzo/SpawnPK-Client/pull/1040), tracked under [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

## Original v309 private source work

I have now independently reconstructed two additional real original `com/a/b/a/b` matrix methods as Java, compiled them alongside the partial matrix owner using Java 9 and **only Java-source companion declarations** (no original JAR/classfile on javac's classpath), and compared all JVM instructions with the SHA-pinned original v309. They reproduce every instruction, bytecode offset, branch destination and resolved call/constant:

| Original recovered selected method | JVM instruction match |
| --- | ---: |
| Package-private 3-float Euler angle extraction `c():float[]` | **108/108** |
| Public alternative Euler angle extraction `d():float[]` | **113/113** |
| **This pass** | **221/221** |

The first extraction calculates Euler angles through a singularity threshold near `±0.999`, otherwise using signed `asin`, `cos`, and double precision `atan2` expressions. The second follows a `cos` magnitude threshold `0.005` and changes the `atan2` branch/axis used near a singularity. The exact original constant bit patterns, float/double conversions and branch order were required for Java9 to generate the same code. These are ACTUAL private Java method reconstructions, not simple class aliases.

Together with R150–R153 the source method inventory now covers **17 selected original matrix method bodies with 632 matching decoded JVM instructions**: R150 six ordinary methods (95), R151 four constructors/reset methods (181), R152 three pool methods (74), R153 two Packet constructor/decoder methods (61), and R154 two Euler methods (221).

The private source artifacts are SHA-pinned separately:
- Partial 17-method original-derived matrix Java ZIP: `c63ebc32e04751655d504d5e747a54aa40a96c338709ea1974837e37355fb745`.
- Three temporary source-only companion class ZIP (unverified implementation bodies): `459e9b5b6931d92a9bf587bbde47e19229d50008514589ab401ed53a7f397f3c`.
- Four-method exact private selection JSON (Packet constructor/loader plus two Euler methods): `1b3c0481d190d199fd8a76499109644db37b8666ffd48bcc94eaac64d15ec701`.
- Original matrix classfile SHA-256: `52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030`. Whole v309 client JAR: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

The private original/source comparison is an **independent** Java9/javap verification, not yet an official run of the GitHub R153/R154 tool against the proprietary originals. It establishes instruction/operand/branch-level parity only; no automatic classfile StackMapTable, full-owner, source dependency closure, client runtime parity or right-to-redistribute acceptance.

## GitHub implementation

R154 safely extends R153's exact SHA-pinned, original-R136-game-dependency-verified **source-only** compiler with optional `--allow-euler-method-bodies`. Without the flag the original two-method Packet loader only is permitted; with the flag an explicit private selection JSON must contain **exactly four distinct methods**, including one original Packet-typed constructor, one same-descriptor original decoder method, and both original `()[F` Euler methods.

Before compiling, it verifies that those two original JVM `()[F` methods are **exactly** the ones in the original owner: one is package-private, one public, both invoke only `java/lang/Math` among external method owners. It demands the same three exact source-support identities already derived from original Packet loader callsites. JDK Java9 then compiles all four source-only class declarations with empty external/original classpath and sourcepath, annotation processing disabled. The selected original-vs-Java-recompiled four methods must match R150's strict resolved JVM Code operand/offset/branch/max-stack/locals/handler comparison; StackMapTable differences are reported separately. Source-only companion method bodies, scaffolding and unselected matrix members are never accepted as original behavior.

Private call (four selected methods):

    python -m spk_recovery.private_v309_matrix_packet_loader_parity_r153 \
      PRIVATE_ORIGINAL_V309.jar PRIVATE_MATRIX_17_SOURCE.zip \
      PRIVATE_UNVERIFIED_THREE_SOURCE_STUBS.zip PRIVATE_SELECTION4.json \
      FRESH_PRIVATE_REPORT.json \
      --matrix-sha256 VERIFIED_MATRIX_SHA256 \
      --support-sha256 VERIFIED_THREE_SUPPORT_ZIP_SHA256 \
      --selection-sha256 VERIFIED_FOUR_METHOD_SELECTION_SHA256 \
      --allow-euler-method-bodies

Cross-platform GitHub tests use **synthetic math-only float-array source methods, not user original source**. They demonstrate exact isolated JVM method matching against an independently compiled original game-linked matrix, and fail closed on missing opt-in, incorrect original method selections, altered Euler source expressions, changed return signatures and R153 regression. No original user/source or client binary is uploaded.

## Remaining source recovery

The full original matrix class is still incomplete: real transformations, quaternion application, `toString`, and scale extraction still require evidence. The support classes and any matrix helper method used only as a compile scaffold remain explicitly unverified; the real `Packet` signed-short name mapping is still unresolved despite R149's body instruction parity. The previous independent 1,271-Java full-source diagnostic remains **516 errors**, because the partial matrix owner and source-only dependencies have not yet been integrated into a clean full-original client Java compile.

Final v309 source tree under `recovered-source/v309/src/` needs complete original-derived source identity, independent external-dependency provenance, original binary exclusion, and runtime/redistribution acceptance; no synthetic CI passes these by themselves.
