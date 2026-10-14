# R153 — original-v309 matrix Packet constructor and decoder Java reconstruction

Scope: original **client-only**, stacked on [R152 #1039](https://github.com/Trexzo/SpawnPK-Client/pull/1039), toward [source milestone #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

## First recovered original Packet-dependent matrix method bodies

The original matrix class `com/a/b/a/b.class` (SHA-256 `52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030`) is an excluded game-linked JVM class under R136. Its original v309 JAR SHA-256 is `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

A **real private** source-code reconstruction has now independently compiled *two* additional methods against Java-source-only minimal dependencies, **never** the original game/client binary. The loader's Java control flow was reconstructed from original bytecode:

- `b(rs.x.e, boolean)`: allocate 16-float matrix and invoke the loader. **11/11** original JVM instructions match.
- `a(rs.x.e, boolean)`: in encoded mode, read six original `B:()I` signed 16-bit Packet values, convert the first three via original `com/a/b/a/d.a:(I)F` for a quaternion-like transform `com/a/b/a/a`, and pass the next three as floats to a translation. In plain mode, loop over all 16 matrix entries and read original Packet `s:()F`. **50/50** original JVM instructions match, including instruction offsets, branch targets, constant and member reference targets.

Both source methods were compiled with `javac --release 9 -proc:none -g:none`, and the complete selected original-vs-rebuilt instruction streams, after ignoring only constant-pool numeric slot IDs, matched. Original/source Java binaries were not placed on the compiler classpath.

**Critical dependency limitation:** three PRIVATE **signature-only Java support classes** were used to allow compilation: a `rs/x/e` Packet interface-shaped class (with unverified `B`/float-reader behavior), a transform `com/a/b/a/a` (with unverified constructor and setter bodies), and a conversion utility `com/a/b/a/d` (with an unverified int-to-float body). The matrix's own `a(transform)` method was also a clearly unverified *compile-only* placeholder. None of these four support method bodies is accepted as original, and they are NOT a substitute for original-source recovery. The original reader `B` is method-body correlated to two same-body candidate Packet readers under R149; its original decompiler identity remains ambiguous.

### Current private source recovery tally

| Reconstruction | Original JVM instruction match |
| --- | ---: |
| R150 six ordinary methods | 95 / 95 |
| R151 two constructors plus identity/zero reset | 181 / 181 |
| R152 factory/release/static pool | 74 / 74 |
| R153 Packet-dependent constructor+decoder | **61 / 61** |
| **Total** | **411 / 411 across 15 selected methods** |

This is an *independent real original-source compile experiment*, not yet a pass of the exact GitHub R153 replay tool. It is not complete matrix-code restoration, classfile identity, full StackMapTable equivalence, source dependency closure or runtime parity. Both the private rebuilt owner and support sources stay in an isolated workspace.

For repeatable private provenance, the SHA-256 of the complete 15-method partial matrix Java preview ZIP is `89ac03c3694044153cbbbe018771c682a2cf400df505984cdfc02a31e8c732df`; the separate temporary THREE source-only support-class ZIP is `459e9b5b6931d92a9bf587bbde47e19229d50008514589ab401ed53a7f397f3c`; the private exactly two selected-method JSON is `5bc1b3d9635bf0c794a95aef1ef110be6bed6bbc4bf2b8cd4cdc24aa56c59987`. These hashes identify local candidate artifacts, **not** publication-ready source.

## R153 GitHub implementation

The new private, SHA-pinned R153 runner:

1. Checks the full original-v309 JAR, one-original-owner Java ZIP, exactly-three-supporting-source Java ZIP and selected-two-method JSON pins *before and after* operation.
2. Uses R136's actual original class-descriptor game-dependency graph to require the matrix class is an excluded, direct-`rs/` game-linked original binary.
3. Reads the selected original constructor and decoder JVM method callsites, requiring the constructor delegates to the decoder. Validates that the THREE provided support-source class identities match **exactly** the original external decoder member-owner references (including an original `rs/` Packet dependency), with each classfile identity existing in the original client JAR.
4. Uses a trusted, parse-only JDK AST declaration checker on the four sources, then compiles with Java 9, empty original/external classpath, empty external sourcepath and disabled annotation processing. No original game binary is loaded or executed.
5. Verifies that the output has **exactly four compiler-created classfiles** (the matrix plus three source supports). Checks only the two explicit selected original methods against decoded JVM instruction/offset/branch/control-flow and resolved CP operand streams, stack/locals and handlers, using the existing R150 strict inspector. Reports StackMapTable comparison separately.
6. Publishes only a sanitized **PRIVATE** report: source/JAR hash pins, selected method/instruction totals, bytecode-match booleans and explicit `support_class_bodies_original_equivalence_accepted=false`, `complete_original_matrix_class_source_accepted=false`, `whole_v309_client_source_compilation_accepted=false`. No original classfiles, Java source, sensitive method maps or game client assets are uploaded to GitHub.

Private use:

    python -m spk_recovery.private_v309_matrix_packet_loader_parity_r153 \
      PRIVATE_ORIGINAL_v309.jar PRIVATE_PARTIAL_MATRIX_SOURCE.zip \
      PRIVATE_THREE_SOURCE_ONLY_STUBS.zip PRIVATE_EXACT_2_METHODS.json \
      FRESH_PRIVATE_REPORT.json \
      --matrix-sha256 VERIFIED_MATRIX_JAVA_ZIP_SHA256 \
      --support-sha256 VERIFIED_UNVERIFIED_SUPPORTS_ZIP_SHA256 \
      --selection-sha256 VERIFIED_SELECTION_SHA256

Hosted Ubuntu/Windows tests use entirely synthetic original Java 9 matrix + actual rs-game owner dependency plus three independently compiled support classes, then a second Java source-only compilation with deliberately **different support method behaviors**, proving only the caller JVM Code—not companion implementation parity—is accepted. Tests refuse changed constructor/decoder control flow, wrong helper owner, extra helper class, altered selected methods or source/original SHA pins. R152 regression is included.

## Remaining

The original matrix's `a(transform)` method, matrix rotations, composition, normal extraction and other operations still require Java source reconstruction; the source-support stubs are unacceptable as final original-derived game implementation. The previously independently measured 1,271-Java private client compilation frontier remains **516 errors** until complete matrix and Packet Java source are integrated into one source tree and retested. The full `recovered-source/v309/src/` tree, original runtime parity and redistribution rights remain outstanding.
