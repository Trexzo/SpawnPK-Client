# Original v311 R118 — 80-class integrated source build (private original comparison)

**Original authority:** Owner-provided v311 game JAR SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. No original game JAR, recovered original Java or compiled game/vendor binaries are included in the public repository.

## Integration, not new original-class discovery

R118 integrates **previously recovered** `rs/k/e$a` (the 3-mode nested renderer enum, accepted in R116 with **50/50 original ordered symbolic JVM instruction matches**) into the verified R117 79-original-name Java9 compilation. The compiler emits the nested class from a Java9 donor outer `rs/k/e`, whose emitted **outer class is discarded** and **not treated as a recovered renderer**. The nested enum's obfuscated enum-field/member identities are restored on copied compiled metadata; no generated JVM executable `Code` or exception-handler changes.

| Metric | Verified R117 | New verified R118 |
| --- | ---: | ---: |
| One Java9 source-generated build, original-named classfile outputs | 79 | **80** |
| Original JVM instructions accounted for in that ONE source-generated build | 8,349 | **8,399** |
| Existing rebuilt class SHA fingerprints unchanged | 78/78 from R106 | **79/79 from R117 (78 R106 + scene node)** |
| NEW distinct original class identities accepted | 0 | **0** |
| Cumulative distinct accepted original v311 classes (across separate source builds) | 116/1,184 | **116/1,184, unchanged** |
| Cumulative distinct original JVM instructions (across separate source builds) | 10,038 | **10,038, unchanged** |

`rs/k/e$a.class` original SHA256 `b5ee5ed752fdcbfd389f40b9457141db371dc58db371327054aa2de1654d5b22`, integrated source-generated SHA256 `6684d96ae9e3c97983a44ff20fb6d055a1a50c858ca9eedf7393d884a09445ff`, exactly the previously accepted R116 rebuilt fingerprint. Existing `rs/a.class` source-generated SHA `cabc38cf4fe192004fdfebd164de22ae846bcdb32ed468534c87f8166ac77e1a` remains identical to R117. Other 78 prior R106 hashes remain identical byte-for-byte. `rs/a` original **24/24** JVM instructions also freshly checked in the R118 integration.

**Important source closure boundary:** the original nested `rs/k/e$a` constant-pool metadata still references the *unrecovered* parent renderer `rs/k/e`. R118 proves an 80-original-named source-generated **compiler** output, with a temporary discarded donor owner, **NOT full original-static-dependency closure or reconstructed outer renderer runtime**. The Java compiler classpath contains only authenticated original-v311 vendor-only GNU Trove (1,595), Google (2,607), LWJGL (967) classes; **zero original `rs/` game binaries** and zero fake implementation classfiles in the selected restored outputs. Other existing reviewed reversible compile-only aliases (including the R117 `rs.a` type/package collision) remain unchanged.

## Original-private verification and refusal checks

Owner-private archive `SpawnPK-v311-R118-80-Class-Private-Integrated-Sources.zip` has SHA256 **`2239377186b27331356d66c58f344b97c0d7974025091d44579e83e94b574023`**, **251,790 bytes / 149 entries**. It contains reconstructed owner-private Java, SHA-pinned manifests, authentic vendor extraction tooling, probes and strict verifier, **NO original JAR, compiled game/vendor binaries, assets or credentials**; it has not been uploaded to public GitHub.

Independent **fresh extraction** followed by exact original SHA/JAR authority check, source and tool hash pin checks, original-versus-new Java9 `javap -p -s -c` class shape/symbolic/offset/instruction parity, exact 80 output set, all 79 prior compiled hashes, plus original-vs-rebuilt behavior probes: **24/24 scene node observations with rebuilt game classes alone** and **17/17 combined renderer mode enum/node observations with the owner-original JAR as trailing RUNTIME-ONLY outer-renderer metadata fallback**. This runtime fallback is explicitly excluded from `javac` compiler input. Previous large scene/render regression suites are retained by compiled fingerprint checks rather than claimed as fully rerun. Full classfile-byte identity is not claimed.

The freshly extracted private archive additionally passed **8/8 negative/fail-closed tests**: unauthorized source edit, deleted donor source, extra Java stub, changed alias compiler, changed enum reflection probe, inflated cumulative class ledger, corrupted original owner JAR, and altered real enum value order with **both Java donor-source SHA and compiled enum-class SHA deliberately repinned**. The final case is rejected by the **actual original-vs-built symbolic JVM instruction comparison**, not by an incidental source hash mismatch.

The [public Java9 synthetic nested-enum source integration regression](../tests/test_v311_synthetic_nested_enum_common_build.py) uses **invented, unrelated** Java types and enum names, with no recovered original game code or binaries. It checks prior-class hash preservation, discard of the donor owner, deterministic nested compiler emission and mutation of real generated JVM code after candidate hashes change. Successful public hosted CI certifies only original-independent synthetic code, **not private original JAR parity**.

Original `rs/k/e` renderer **17/36** direct accepted project references, original `rs/a/a` scene model **5/14**; neither blocked parent recovered. Seven provisional tile classes remain excluded, as do whole-client build, original classfile bitwise identity, runtime UI/native graphics and gameplay acceptance.

**Keep [draft PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) UNMERGED.** Manual game testing is not needed for this source-only integration milestone.
