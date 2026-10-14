# R155 — original-v309 matrix transform projection source recovery

Client-only source restoration, stacked on [R154 #1041](https://github.com/Trexzo/SpawnPK-Client/pull/1041), tracked by [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

## Recovered original method (no longer compile-only placeholder)

The original matrix owner `com/a/b/a/b.class` contains a package-private transform projection method, descriptor `(Lcom/a/b/a/a;)V`. It converts twelve verified float fields of an original transform/quaternion-like object into the sixteen float slots of the matrix (setting the fourth, eighth and twelfth slots to zero and the final homogeneous coordinate to one). Before this pass, the partial Java used an **unverified empty placeholder** for this method solely to compile the Packet-dependent decoder that calls it. That placeholder was never accepted as original behavior.

I reconstructed the **actual original Java field assignment statements** from the original JVM Code and compiled them with a Java-source-only transform support class containing the corresponding 12 float field declarations (but NO accepted original transform behavior). The original versus Java9-recompiled method yielded **93/93 identical original JVM instructions**, bytecode offsets and resolved field references. The method does not call external methods; its original field usage fully determines the matrix/transform owner references. The private proof did not use original client binary dependencies on the javac classpath.

The privately reconstructed partial matrix class now covers **18 original selected method bodies / 725 matching JVM instructions**, with source bytes held outside public GitHub:

| Private stage | Matched original JVM instructions |
| --- | ---: |
| R150 six ordinary matrix methods | 95 |
| R151 two constructors and identity/zero reset | 181 |
| R152 pool factory/recycle/static initializer | 74 |
| R153 Packet-dependent constructor and loader | 61 |
| R154 two Euler-angle calculation methods | 221 |
| **R155 original transform-to-matrix field projection** | **93** |
| **Total** | **725** |

Exact private preview pins: partial 18-method Java ZIP SHA-256 `f319c5dd2878a68b982bb2f4de797126e1ac7bd183472d9b1c96bfe251090835`, updated **source-only** three-support-class ZIP (adding original-type field declarations without pretending body equivalence) `66339f959fe70e448346d05ef46cef912183b05628ce93e58bbdd3ae62d9477b`, original 5-method selected JSON `d643d0a27d925bb4de816f7927e69aeef354019772db3828c46297a0f1051fee`. Whole original v309 JAR `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`, matrix owner binary `52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030`.

## GitHub verifier extension

R155 adds a separate, explicit `--allow-transform-projection-method` option to the SHA-pinned R153/R154 private **source-only compiler**. The selection must contain one actual original Packet constructor, its same-signature decoder, optionally the two math-only original Euler methods with independent opt-in, and exactly ONE new projection method `(L<original transform source owner>;)V`. The original projection must be package-private, use no method invocations, reference only original matrix/transform fields, and have a JVM method body exceeding a minimal size and containing at least eight original field references. Its target transform owner must be one of the EXACT three original decoder-dependency source-class identities already proved from original JVM callsites.

R155 then compiles the exact four private source classes with `javac --release 9 -proc:none -implicit:none`, empty project/class binary classpath and sourcepath, and uses R150's strict decoded JVM opcode/offset/CP-resolved operand/branch/stack-limits/exception-handler comparison on **all selected original methods**. StackMapTable representation is separately tracked, never silently treated as identical original Code metadata. Companion/support bodies, unselected methods, original full matrix class equivalence, runtime and publication rights are never accepted just because selected methods match.

Private invocation extends R153:

    python -m spk_recovery.private_v309_matrix_packet_loader_parity_r153 \
      PRIVATE_ORIGINAL_V309.jar PRIVATE_PARTIAL18_MATRIX_SOURCE.zip \
      PRIVATE_THREE_JAVA_SOURCE_SUPPORTS.zip PRIVATE_EXACT_5_SELECTED.json \
      FRESH_PRIVATE_REPORT.json \
      --matrix-sha256 VERIFIED_PRIVATE_MATRIX_ZIP_SHA256 \
      --support-sha256 VERIFIED_SOURCE_SUPPORT_ZIP_SHA256 \
      --selection-sha256 VERIFIED_PRIVATE_SELECTION_SHA256 \
      --allow-euler-method-bodies --allow-transform-projection-method

Hosted Ubuntu and Windows fixtures use entirely synthetic original JVM matrix/transform classes and two math-style Euler readers. The recovered synthetic Java source projection stores 16 slots from 12 transform source fields; changing one field operand, omitting support member declarations or omitting projection opt-in vetoes the entire selected-source verification. Previous R153 and R154 original-JVM synthetic tests must remain green. **No real SpawnPK original Java, classfiles, proprietary assets or original-derived method source is included in public CI.**

## Still missing

The matrix's original large transformations/compositions, scale-vector extraction and `toString` methods are not fully reconstructed. The original `rs/x/e` and transform source-only dependencies are NOT verified complete original Java implementations. The independent whole 1,271-Java source compile still has the earlier measured 516 errors; integrating incomplete matrix source is not a clean full-client source build or a new error-count reduction. Rights/provenance checks remain before public original-derived source-tree publication.
