# R192 — reproducible original v309 four-owner source-tree compiler frontier

Client-only original source milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004), stacked on R191 [PR #1085](https://github.com/Trexzo/SpawnPK-Client/pull/1085). This measures **real JDK-only compiler diagnostics**, not conceptual progress.

## Exact private source snapshots

The authoritative pinned private baseline `recovered-source/v309/src` contains **1,278 Java source files**, ZIP SHA256:

`dd68b18a4e60e7d9b2431811a1531f4e33bfa75ac1adb9a4f07100a64e99d6da`

The new experimental private overlay adds only four original-evidenced real Java source owners:

| Original owner | Private one-source ZIP SHA256 | Original Java text SHA256 |
| --- | --- | --- |
| rs/q/a.java (ISAAC cipher, R182) | 09ad2bbf2a8fd83c26fb3a2c9c22de0a08ae77ab54ba5ad4c88f4d055f91d431 | f09961878757eb848c17efc7b950f8cf6393a5fc7935f7fba8b5a7b8d8f6437c |
| rs/v/a.java (Signlink outer, R188/R189) | a7172b3aae3a794bbd5a59f6de085a7ee7b68749a117671d5cf6b47a0fcd5288 | 03d6b77ffa1b3eb77ee24d562b38a699e493f01739ab9303c17d7f344c859f77 |
| rs/v/a$a.java (direction enum, R190) | 367c02a4e7fcc9ba9d7eb5bb99504751c6c17cd7d3eaf5717c7f2b32942dc766 | 4127bad45575bb6e061eb0f811231cf3d41681444ba4851c7937159f56a99f63 |
| rs/k/j.java (platform enum, R191) | 07d1e38deebe95ede0297d08ca2922bea33c4518af22af6ffe1d1ed1ba9ecfa2 | 4246c2c97e66c9b63cd2ef8af25b048f763c02c4594d18cfffc4deb086b8d43d |

Overlay ZIP SHA256:
**d5e522ef9f7573b4e6009eb8fffee561767608b19a996791de4af8fe4c57c47b**

Exactly **1,282** Java files; all **1,278 previous file bytes are identical**. The overlay is experimental, not an accepted publishable canonical tree. It does not contain the five invented helper declarations used in isolated R191 proofs or any original compiled classfile/JAR. Original-derived source and private overlay remain outside public GitHub.

## Real whole-source compiler comparison, 2026-10-15

Both snapshots were compiled independently under identical source-only JDK21.0.12.1 options:

`javac -J-Xmx4g --release 9 -g:none -proc:none -implicit:none -Xmaxerrs 10000 -classpath EMPTY -sourcepath EMPTY -d DEST @sources.args`

No original client JAR, downloaded third-party packages or external .class files on compiler classpath. The exact Java9 and javac diagnostic error summary was counted from complete stderr, not inferred from a capped 100-error output.

| Compiled snapshot | Java files | Javac errors | Javac exit |
| --- | ---: | ---: | --- |
| Pinned original baseline | 1,278 | **2,339** | 1 — fail |
| Four-owner source overlay | 1,282 | **2,346** | 1 — fail |
| Actual delta | +4 | **+7** | Still fails |

Baseline diagnostic stderr SHA256:
`a8bc97a9ccccafd016e30e25f5633cb94ff94a71a491fdce7e2a194609d2e11e`

Overlay diagnostic stderr SHA256:
`c1e1c02d802b8575c0fe501b0f3edcf9be68f1c5e02916165718415d7a13485b`

The additional seven diagnostics originate from **new real rs/v/a Java** references to five still-unrestored original supporting class implementations: rs/w/c (two package errors), rs/f/a (two package errors), and rs/secure/{a,b,c} (three missing-type errors). Previously existing errors persist, especially unresolved source/third-party dependencies (e.g., logging, injection, annotations, graphics/cache types). **No compiler-error reduction is claimed; the changed count is an increase of seven caused by actual source integration.**

This is a **different input snapshot** from the R179 private Packet-overlay tree with 2,343 errors. Do not compare those error counts as a branch-to-branch regression without first constructing one shared baseline containing both verified source selections.

## GitHub R192 tooling and acceptance gates

The R192 verifier:
1. Requires the exact original 1,278-file baseline ZIP and four exact SHA-pinned original-named private source ZIPs.
2. Refuses duplicate/case-colliding archive entries, symlinks, unexpected path prefixes, source owner mismatches, overwrites of existing sources, corrupt SHA pins and non-fresh output paths.
3. Creates one private 1,282-file experimental ZIP preserving every old Java byte; refuses to include invented helper scaffolds.
4. Replays identical source-only JDK9 full-tree compilation, requiring complete untruncated diagnostic summaries from both snapshots.
5. Reports both error totals, delta and source-file preservation, while retaining explicit FALSE runtime/game execution/original-binary-fallback claims.

Public Ubuntu/Windows CI tests use invented unrelated Java sources and verify byte preservation, an intentional missing Java type causing an increased compiler-error frontier, digest failures and malicious/unsafe ZIP entry rejection. No original-derived Java/JAR enters public CI.

## Next recovery worklist

Recover original client source for the five direct Signlink supporting owners: rs/w/c (MIDI/audio), rs/f/a (configuration), rs/secure/a, rs/secure/b, rs/secure/c (identifier/environment). Recompile the 1,282-source candidate without inserting fake helpers. Also merge the separately recovered R179 original Packet Java source into a SHA-pinned, COMMON experimental source baseline before making cross-PR compiler comparisons.

Original nested enum source in R190/R191 preserves semantic enum names and aliases, not exact classfile/StackMap/InnerClasses binary identity. Original source licensing/redistribution is still unresolved. The entire v309 client is NOT source-compiled or runtime-tested. Keep all PRs draft until honest closure gates pass.
