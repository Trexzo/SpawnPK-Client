# Original v311 R98 — compiler-generated renderer switch table source parity

**Owner-private original authority (2026-10-23):** supplied `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The original game JAR, private recovered Java, private source/JVM probes, compiled game classfiles and original GNU Trove vendor binaries are **never uploaded to public GitHub**.

## One new compiler-generated original class, not one hand-authored class declaration

The genuine original `rs/k/g.class` is a Java9/JVM compiler-generated **enum switch translation table**, with a synthetic static final `int[] a`, exactly one class initialization method, **NO constructors or ordinary methods**, and three ordered `NoSuchFieldError` exception handlers.

| Original JVM class | Original class SHA-256 | Independent source-generated/inverse-restored class SHA-256 | Exact original JVM instructions |
| --- | --- | --- | ---: |
| `rs/k/g.class` | `8950e92d3c651b2393265f36338fbb90ac1930d751f14bab7af43532da03f8a8` | `74a50e51a5cace68c51499b2c3821ddb9d945a387a7df0347e75cb6c689aab21` | **26/26** |

**Source distinction:** The owner-private `src/rs/k/g.java` contains an independently reconstructed Java `switch` **donor owner** type rather than pretending that `rs.k.g` was written as an ordinary Java class. Compiling this original switch-order source with `javac --release 9` yields a synthetic owner-nested switch table class automatically, with **exactly the original 26 JVM instructions and all three original exception handlers**. A strict, separately SHA-pinned reversible transform restores the compiled table's JVM class identity, field name, obfuscated external `rs/k/a/c` enum field names and compiler-generated owner metadata on **copied** classfile bytes. It does not edit its executable JVM `Code` or exception table, nor the enum runtime `Enum.name()` values.

There are **69 previously recovered original Java source-type declarations PLUS ONE original switch donor Java source** (70 compiler input files); javac emits **71 temporary outputs** (69 original classes, synthetic switch-table class and donor owner), then the donor owner output is **explicitly discarded**. This leaves exactly **70 original-named recovered JVM classfiles** in the independent build. Do **not** call these 70 ordinary original Java class declarations or claim they represent 98 simultaneously compiled original sources.

## Exact closed build and behavior

One independent `javac --release 9 -proc:none -g:none` invocation generates a **70-original-classfile dependency-closed output / 7,022/7,022 original matching JVM instructions accounted for**. All **69/69 previous R97 rebuilt original-class SHA-256 fingerprints are byte-for-byte unchanged**; their 6,996 old original JVM matches are retained by original-certified identical compiled byte hashes. The **26 new instructions** and complete original class/member declarations/branch offsets/exception handlers were freshly independently disassembled against the original v311 JAR.

The original `rs/k/g` has just one explicit project-class dependency, `rs/k/a/c`, now recovered in R97. **Zero temporary source stubs and zero missing explicit `rs/` project dependencies**. The compiler uses real GNU Trove vendor classfiles extracted temporarily from the exact SHA-pinned original JAR: exactly **1,595 vendor-only `gnu/trove/` entries and ZERO original game `rs/` classfiles**. The previously reviewed aliases for `rs/k/a`, `rs/k/c` and the seven vendor map/nested classfiles are unchanged. This is explicitly **not** a zero-binary compiler classpath; real vendor-only binaries are used, never game binaries or stubs.

The bounded headless original-vs-source-built JVM switch behavior comparison matched **15/15 NEW cases**: all three enum names/ordinals, all three original obfuscated enum field identities, all three switch-map slots (`OFF→2, ON→1, ADAPTIVE→3`), `values()` clone behavior, reflective synthetic field/class flags and the absence of constructors/ordinary methods. Earlier R97 behavior cases are previously certified and **were not rerun** here. This does not establish a complete working graphics renderer or full client.

## Independently clean-extracted archive and seven refusals

Private owner-only source/verifier ZIP: `SpawnPK-v311-R98-Renderer-Switchmap-70-Class-Private-Sources.zip` SHA-256 **`fff84c296893cfcb6f061b5cef43d284987021b4ebd80f50ea94e073e93aa438`**. The archive has 70 Java source files (69 recovered source types + one synthetic switch donor), exact original/source/rebuilt manifests, private compiler/verifier, behavior probe and seven refusal trials. **ZERO original client JAR, classfiles, jar files, vendor binaries, fonts, assets, credentials or account data**.

Independent fresh ZIP extraction passed all SHA-pinned original-authority/source/compiler/enum-restorer/vendor checks, compiled the full 70-original-classfile output, verified all 69 prior SHA fingerprints, compared 26/26 newly original JVM instructions and 15/15 original-vs-rebuilt behavior cases. **Seven/seven deliberate invalid cases passed**, refusing modified donor source, missing donor source, wrong original whole-JAR SHA, forged vendor binary SHA, unreviewed class alias, unreviewed switch-restorer modification, and changed generated JVM switch instructions **despite re-pinning both donor source and compiled class SHA values**.

## Audited distinct counts and remaining blockers

Correct previous R97: **97 distinct original-v311 recovered classes / 8,192 exact original JVM instruction matches across separately certified source builds**. New R98 adds **one genuine original compiler-generated classfile / 26 instructions**, giving **98 distinct accepted original-v311 classes / 8,218 original JVM instruction matches cumulatively across separate accepted builds**. The **largest single source-generated closed original-name output is 70 classfiles / 7,022 original instructions**, not a simultaneous 98-original-Java-source rebuild.

[Public synthetic-only generated enum switch-table restoration tool](../src/spk_recovery/switch_table_identity.py) and [three unrelated toy Java9 positive/negative tests](../tests/test_v311_synthetic_compiler_switch_table_parity.py) verify the same compiler-generated-shape principle without the user's original game code or private switch donor. Hosted CI does not certify the private original-JAR replay and must be checked separately.

The large original `rs/k/e` renderer and `rs/a/a` scene model remain unrecovered. The seven earlier provisional `rs/I` and tile-class source candidates remain excluded. Original whole-classfile binary equality, source authorship/text identity, native/OpenGL/asset closure, authenticated client and gameplay have **not** been established.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT, UNMERGED**.
