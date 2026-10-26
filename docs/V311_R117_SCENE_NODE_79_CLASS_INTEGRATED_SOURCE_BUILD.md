# Original SpawnPK v311 R117 — 79-class integrated source-build certification

**Owner-private original JAR authority:** SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. All reconstructed Java, compiled original/rebuilt game classfiles and the owner-private verifier remain **off the public repository**.

## Real source-closure improvement; no new cumulative class acceptance

R116 accepted **116 DISTINCT original-v311 classes / 10,038 exact ordered symbolic JVM instructions across SEPARATELY certified private Java9 builds**. R117 adds **zero newly accepted identities and zero new distinct instruction witnesses**; it promotes a previously accepted scene-node type `rs/a.class` into the already established R106 common source group. The largest original-named compilation advances from **78 classes / 8,325 instructions** to **79 classes / 8,349 accounted original JVM instructions**, preserving **78/78 original R106 previously compiled SHA256 fingerprints byte-for-byte**.

| Original source-generated class | Owner original SHA256 | New common-build output SHA256 | Ordered original JVM instruction match |
| --- | --- | --- | ---: |
| `rs/a.class` — linked scene node, **already accepted in R116** | `7c33983b6e49dc2cd8b4b5bde2bd0550a4977c1eaa483025630b5c16105e735f` | `cabc38cf4fe192004fdfebd164de22ae846bcdb32ed468534c87f8166ac77e1a` | **24/24** |
| Previous source-generated R106 accepted group | Previously SHA-pinned class-by-class | **All 78/78 hashes unchanged** | **8,325 retained** |
| **Single source build (not cumulative distinct ledger)** | | **79 original-named classes** | **8,349 accounted** |

### Java source/JVM identity collision resolved

Canonical original `rs/a.java` defines **class `rs.a`**. Already accepted Java sources `rs/a/d.java` and `rs/a/i.java` define **package `rs.a`**. Both cannot coexist as canonical Java9 source names in one `javac` invocation. The updated compiler stages a temporary `rs/RecoveredSceneNodeV311` with only its class declaration, self-referential field types and constructor renamed. A bounded postcompile constant-pool alias restoration on copied classfile outputs restores the original `rs/a` class and descriptors. Original source files remain unchanged. No emitted JVM executable `Code` or exception handlers are modified. All preexisting 78 compiled SHA fingerprint comparisons pass unchanged. Source-set selection is exact: 79 original Java inputs, zero fake source implementation stubs.

Vendor-only compile dependencies are actual GNU Trove (1,595 classes), Google (2,607) and LWJGL (967) binary classes authenticated and extracted at verification time from the original owner-JAR and confined to their third-party namespaces. **Zero original `rs/` game class binaries on the javac classpath**, and no original compiler classfiles are redistributed.

### Clean-extracted R117 private verifier results

Owner-private archive `SpawnPK-v311-R117-79-Class-Private-Integrated-Sources.zip` SHA256 **`0668aa789d60141ca74ccaffc9a7e7322f20f43595e5a5a66fa3df4f7d2dc542`**, size **242,829 bytes** (143 entries). It includes reconstructed owner-private Java and manifest/verifier/probe tools; it contains **NO original client JAR, compiled classfiles, third-party vendor binaries, game assets or credentials**. Never upload this ZIP to the public repo.

Independent clean extraction followed by exact original-JAR SHA/source/tool pin verification, new `rs/a` class SHA and original `javap -p -s -c` symbolic/declaration/offset checks, 78 previous rebuild fingerprint checks and the exact 79-original-name output-set audit **PASSED**. The integrated rebuild is tested *without* the original JAR as a runtime fallback: a separate process using only rebuilt game classfiles matches the original-JAR baseline in **24/24 linked-node reflection and unlink behavior observations**. That is only a bounded node runtime test, not renderer/GUI/gameplay acceptance.

**8/8 clean-extracted fail-closed negative checks PASSED:** unreviewed new-source edit, missing new source, fake extra source stub, compiler alias tool edit, probe modification, artificially inflated recovered-class count, wrong original-JAR authority, and an altered linked-node JVM algorithm after **repinning both new source and built class SHA values**. The last still fails direct original-vs-built JVM instruction comparison. Recovered old R106 classes retain their earlier behavior certification, but the entire R106 behavior battery has **not** been rerun in this R117 verification.

[Public synthetic-only regression](../tests/test_v311_synthetic_source_alias_integration.py) contains completely invented toy Java9 sources, models a source class/package collision, checks unchanged classfile fingerprints and rejects actually modified JVM algorithm despite refreshed hashes. Its hosted CI is a separate safety check, **not a replay of private owner-v311 parity**.

### Accurate remaining scope

- **Accepted cumulative ledger remains 116 / 1,184 distinct original-v311 classes and 10,038 original matching JVM instructions across separate private source-build islands.**
- **Largest single original-named source-generated group is now 79 classes / 8,349 original instructions.**
- Blocked original renderer `rs/k/e` direct dependencies accepted **17/36**; original scene model `rs/a/a` **5/14**. Neither blocked parent is source recovered.
- Seven provisional tile classes remain excluded; whole original client compilation, original classfile complete binary identity, native/GPU/rendering, assets and gameplay are unverified.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**. No manual game test required for source-only R117.
