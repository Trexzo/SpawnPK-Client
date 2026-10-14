# R156 — recover original v309 matrix StringBuilder rendering as Java source

Original client-only Java reconstruction; stacked on [R155 #1042](https://github.com/Trexzo/SpawnPK-Client/pull/1042), milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

## Real original-v309 method source reconstruction

After R155's first 18 recovered matrix Java method bodies (725 original JVM instructions), I reconstructed the actual `toString():String` method of the original matrix owner `com/a/b/a/b.class` from the original JVM Code. It starts a `StringBuilder`, invokes both previously reconstructed original Euler-angle readers, renders all 16 matrix elements in a 4×4 nested row/column loop, includes separators, and clamps near-zero float values using a float threshold whose double-precision comparison is the original JVM value `9.999999747378752E-5d` (the double-promotion of a `1.0E-4F` threshold).

Compiling that private recovered Java source with `javac --release 9` against the matrix source plus **source-only unverified support declarations**, but NO original client binary/Jar in the javac classpath, yields **60/60 original JVM instruction matches**. All original offsets, branch targets, Math.sqrt, StringBuilder calls, float/double conversions and constants match. No original source text was published to GitHub.

**Updated independently rebuilt partial matrix owner: 19 actual original-derived Java method bodies and 785/785 matching original JVM instructions**:

| Real private recovery stage | Original instructions |
| --- | ---: |
| R150: 6 operations | 95 |
| R151: 2 constructors, identity + zero reset | 181 |
| R152: matrix pooling + static initialization | 74 |
| R153: Packet constructor + decoder | 61 |
| R154: 2 Euler methods | 221 |
| R155: 16-element quaternion/transform projection | 93 |
| **R156: toString()** | **60** |
| **Total: 19 methods** | **785** |

Private SHA-pinned preview identifiers: full partial-19 matrix Java source ZIP `afbf3c80ae94c5c123638e3af0b03c516fa02a9443ffd33936c3e9e10cf2c541`, same source-only three-support-class ZIP `66339f959fe70e448346d05ef46cef912183b05628ce93e58bbdd3ae62d9477b`, explicit six-selected-method JSON `2ac3e32282f9ed0c0deabd54ffbca73606ca170944400520975cd3bcfbcc5767`. Original matrix JVM owner SHA-256 `52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030`, full v309 original SHA-256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

## GitHub source-only verification extension

R156 adds a separate `--allow-matrix-string-method` flag to the R153/R154/R155 exact-SHA-pinned private source compiler. With this flag it permits exactly one additional original `toString:()Ljava/lang/String;` method, **only when both Euler-angle methods are also explicitly selected**. The original bytecode must prove a public `toString` with original call edges to both original Euler methods `c` and `d`, original `java/lang/Math.sqrt(D)D`, and `java/lang/StringBuilder`. No other class named `toString` can replace that original witness. The support-owner graph must remain the same exact three R136-confirmed source-only class dependencies, and the code compiles with a completely empty original/external binary classpath and no annotation processing.

The selected original vs independently compiled Java Code must pass R150's strict resolved opcode/offset/operand/branch/stack/handler comparison. StackMapTable identity is recorded separately, and any unselected class members, supporting source-only class bodies or synthetic compile-only scaffolding remain unaccepted original behavior.

Private invocation additionally passes:

    --allow-euler-method-bodies --allow-transform-projection-method --allow-matrix-string-method

against the exact six-method private selection file and private recovered Java ZIP. No private actual original source, original JVM binary, owner/member maps or assets are committed to GitHub.

Hosted Ubuntu/Windows synthetic tests exercise a distinct synthetic StringBuilder/math-loop source method and its synthetic independently compiled original game-linked matrix, checking exact original callsite/Code witnesses. Negatives mutate the text delimiter, floating point threshold, original method descriptor, independent string-method opt-in and Euler dependency acceptance. The R155 regression tests run as well.

## Remaining original source-tree work

The original matrix class still has several complex math/transform operations and a scale/vector extraction path requiring separately reconstructed source types. The accompanying source-only `rs/x/e` Packet/transform utility **implementation bodies have not been accepted** as original-equivalent. The previously measured independent full 1,271-source v309 javac frontier remains **516 errors**, with no new whole-client compilation or runtime claim. The private R156 Java instruction comparison is independent and needs exact GitHub CLI private replay to complete acceptance. Full `recovered-source/v309/src/` and redistribution rights are not yet achieved.
