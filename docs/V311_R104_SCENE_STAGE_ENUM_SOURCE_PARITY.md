# Original v311 R104 — scene-stage enum source parity and 76-class build

**Owner-private original authority:** `client(20261021-111920).jar`, SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Neither original game JAR, private recovered Java, compiled game/vendor binaries, proprietary probes or game assets are committed to public GitHub.

## One genuinely new original v311 scene-model dependency

| Original JVM class | Original class SHA-256 | Independently source-built, original-name restored SHA-256 | Exact original JVM instructions |
| --- | --- | --- | ---: |
| `rs/l/f/a.class` — 27-value scene/render-stage event enum | `93b9117a5c367ac92bac5b9409c1e6501fa51c81d7f8ba004f744a06e5090dcf` | `49248767a8a9f18c54558a134cb1b517d463af559223c5f94e505d918798712b` | **316/316** |

Its independently reconstructed original-name Java9 source preserves all 27 original runtime `Enum.name()` values, original ordinal order, both constructor forms, per-stage `B` flags, and exact class/field/method declarations, symbolic JVM operands, bytecode offsets, branches and generated enum helper JVM identities. Constant-value/declaration metadata also matches. Numeric constant-pool indexes alone are normalized in ordered disassembly comparisons; **complete original classfile binary identity and original Java source-text identity are not claimed**.

The original `rs/l/f.class` color-packing utility exists as a JVM class, while the event enum's JVM name is `rs/l/f/a.class` (Java package `rs.l.f`), a legal JVM but illegal simultaneous Java source naming combination. A strictly reviewed **disposable compile-only rename** of the already recovered `rs/l/f` utility to `rs/l/RecoveredColorPackingV311` allows compiling both original sources. All copied JVM class metadata is inverse-restored to the original type name after compilation. The obfuscated enum static field and compiler-generated helper names are restored **only in copied emitted classfile member metadata**, without replacing enum string literals or changing executable `Code`.

## Actual independent source build and real behavior

All 75 previously certified R103 original classfile outputs, plus this **one new source-recovered enum**, build together as **76 original-named Java9 classfiles / 7,825/7,825 original JVM instruction matches accounted for**. All **75/75 previous rebuilt class SHA-256 fingerprints are unchanged**. The previous R103 7,509 instruction matches retain their certification via identical compiler outputs; only the new 316 instructions were freshly original-vs-rebuilt disassembled. The compiler inputs are **75 recovered original Java type source declarations plus the already-reviewed synthetic enum switch-table donor**; the discarded donor owner is not counted as an original class. There are **zero temporary Java source implementation stubs** and **zero missing explicit original-project static class dependencies**.

The compiler has only authenticated **real third-party vendor** binary dependencies extracted from the SHA-pinned owner original JAR: GNU Trove (1,595), Google (2,607) and LWJGL (967) `.class` members; **zero original `rs/` game binaries** are on the compiler classpath. These original-derived vendor binaries are not publicly distributed or included in the private source ZIP.

The **165/165 new headless JVM original-vs-rebuilt behavior transcripts match exactly**: for each of 27 stages, original display string, `name()`, ordinal, boolean stage flag, original obfuscated constant-field identity and `valueOf`; also `values()` cloning, enum count and invalid name behavior. The R103 behavior cases retain their previous certification but were **not rerun** here. This is not a native rendering, shaders, OpenGL or authenticated gameplay test.

## Fresh clean archive replay and refusal tests

Owner-private source/verifier ZIP: `SpawnPK-v311-R104-Scene-Stage-76-Class-Private-Sources.zip`, **188,192 bytes**, SHA256 **`5aa2a3efd00a40cee2d5ff1c9ac159fe412f87e44f2830f97b433f11250c01e4`**. It contains **76 reconstructed Java source inputs**, previous and current pin manifests, reproducible source compiler, source verifier and JVM probes (plus no game binaries). The archive was freshly extracted and independently replayed with the exact owner-held original game JAR. Its full source/class hash closure, all 75 previous classfile fingerprints, new exact original 316 instructions and 165 new original-vs-source-built behaviors passed.

**Eight/eight deliberate invalid cases failed closed from the clean extraction:** modified Java source, missing original-name source, wrong original JAR SHA, changed vendor-class SHA, unreviewed `rs/l/f` compiler alias, changed compiler tool, changed enum member-identity restorer, and a changed JVM constructor instruction **even after re-pinning both reconstructed source and independent classfile SHA hashes**.

The ZIP contains **no original game JAR, compiled client `.class`/`.jar`, vendor binaries, native libraries, assets, font files, accounts or credentials**. Never upload owner-private original-source reconstructions to this public repository. Public synthetic Java9 tests use separate toy classes only.

## Audited accepted totals and blockers

R103: **103 distinct recovered original-v311 classes / 8,705 matching original JVM instructions across multiple certified source-build records**. R104 adds one genuinely new original class / 316 instructions → **104 distinct classes / 9,021 matching original JVM instructions cumulatively**. This is **NOT one 104-source compilation**: largest currently verified single source-generated compilation has **76 original-named classfiles / 7,825 matching JVM instructions**.

Original `rs/a/a` scene model directly references the new enum `rs/l/f/a`, so its previously missing **11 of 14** direct original project dependencies fall to **10 of 14**, based solely on currently accepted source classes. The large `rs/a/a` scene model, `rs/k/e` renderer and seven provisional `rs/I`/tile original classes remain unaccepted. OpenGL, native/vendor runtime closure, complete 1,184-class original source recovery, full classfile byte identity and live gameplay are **not proven**.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**. Hosted GitHub CI is synthetic-only and must be checked independently from this owner-private original-JAR replay.
