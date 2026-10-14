# R150 — six independently rebuilt original-v309 matrix Java methods

Client-only original-source recovery; stacked on R149 #1036, milestone #1004. The full recovered-source/v309/src tree remains incomplete.

## Real private original-v309 evidence

The exact original non-rs game-linked matrix class is an 8,172-byte JVM class. It is one of the eight R136-excluded non-rs game-linked classes and must not be restored by adding its original binary back as a compiler dependency.

A private Java source fragment reconstructed from the original JVM Code was compiled with Java 9 and **no original client binaries on the compiler classpath**. Exactly six method bodies matched their original JVM instruction offsets, opcodes, member references and constants:

| Recovered original method behavior | Matched instructions |
| --- | ---: |
| Copy 16 floats to another matrix | 9 / 9 |
| Uniform float scale forwarding | 6 / 6 |
| Three-axis float scaling | 18 / 18 |
| Elementwise matrix addition | 21 / 21 |
| Array-backed hashCode | 12 / 12 |
| Elementwise equals(Object) | 29 / 29 |
| **Total** | **95 / 95** |

Original matrix class SHA-256: 52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030.
Original full v309 JAR SHA-256: ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38.

This is a real source implementation recovery, but **ONLY of six original method bodies**. The private isolated Java fragment also contains a deliberately **unverified reset/initializer placeholder** needed so the selected scale method can compile its original method invocation. Neither that placeholder, the constructors, static pooling, the Packet-dependent matrix loader nor any other original methods are accepted. The private recovered-source candidate is not published to public GitHub pending authorization.

## New reproducible GitHub acceptance gate

R150 adds a private replay tool that accepts three separately SHA-pinned inputs: the whole original v309 JAR, a one-class original-owner-path Java ZIP, and a bounded explicit private selection of exact original method names/JVM descriptors. The source is compiled using Java 9, annotation processing disabled, an **empty original/project classpath** and empty sourcepath. No original game class can be used as a binary fallback.

The tool first uses R136 to prove that the original owner is part of the excluded original rs-game-linked non-rs class set. It verifies one exact Java source owner and a bounded method selection (constructors and class initializers are excluded). It then decodes both original and independently compiled JVM Code and compares **all selected method** access flags, code length, max stack, max locals, opcodes, offsets, normalized resolved constant-pool operands, control-flow targets and exception handlers. StackMapTable agreement is **recorded separately**, and mismatch prevents full method-metadata parity. Unknown instructions fail closed.

Outputs are sanitized aggregate counts, SHA pins and a private witness digest; original Java source, private method names, class bytes or account/cache assets are never sent to GitHub. No unselected methods, artificial compilation scaffolding, whole-owner semantic parity or source-release rights are inferred from a passing result.

Private usage:

    python -m spk_recovery.private_v309_matrix_source_method_parity_r150 \
      PRIVATE_ORIGINAL_v309.jar PRIVATE_ONE_CLASS_SOURCE.zip \
      PRIVATE_METHOD_SELECTION.json FRESH_PRIVATE_REPORT.json \
      --source-sha256 VERIFIED_SOURCE_ZIP_SHA256 \
      --selection-sha256 VERIFIED_SELECTION_SHA256

The private method selection is a JSON array of exact name/descriptor pairs, and the Java source ZIP contains exactly one file at src/main/java/com/a/b/a/b.java.

## Cross-platform proof and remaining work

Ubuntu and Windows CI build a synthetic rs.Game class and a linked non-rs ext.Matrix original, plus a separately recompilable Java source fragment. The source matches six selected methods while deliberately using different/unaccepted reset scaffolding. Tests reject changed selected method instructions, an attempted constructor selection, a missing unrecovered game method, and SHA mismatches. The synthetic test validates the gate; the independent original-v309 compilation above validates the initial six source bodies.

Next restore the remaining matrix constructors, reset/init, static pool and Packet-dependent decoding methods with original bytecode and code-attribute evidence. Original Packet short readers remain name-ambiguous even after R149 instruction parity. The previous whole 1,271-Java source diagnostic baseline remains **516 compiler errors**, with no improvement claimed from this still-partial matrix owner.
