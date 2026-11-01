# R352 — recovered full v309 source: independent clean build and readable pass 1

**Correct repository:** `Trexzo/SpawnPK-Client`. This work is separate from production v312 and from the misplaced `fullspkclient-private` diagnostic track. **The original derived source, private dependency JARs and runtime evidence remain owner-private**, not published in this public Git repository.

## Full R315 archive actually recovered from owner Library

The exact file `SpawnPK-v309-R315-Full-Recovered-Source-Private.zip` was located, materialized and verified:

- Archive bytes: **24,339,390**
- Archive SHA-256: `e46a213ba949dc0a2f420a040b5c9d38451c0923e3ea39917a5d2eb3c9b2fa28` (historical pinned hash matched)
- Inner `R315_MANIFEST.json`: **1,277** `source/**/*.java` files, each independently compared to its SHA-256 in both `R315_MANIFEST.json` and `MANIFEST.json`
- Sources include actual `rs/Client.java` (**898,413 bytes**), `rs/Configuration.java` and `rs/gui/Launcher.java`; the later R315 Client.java SHA differs from the older R211 candidate
- `source/**/*.java` total: **8,116,215 bytes**
- Two pinned, private, third-party dependency archives: `R218.jar`, `R239_filtered.jar`; inspection confirmed **zero `rs/` classfiles in each** (9,327 and 9,326 non-rs class entries respectively)

Unlike the previous R351 1,275-file R211 candidate, the R315 ZIP has the **full 1,277 indexed Java source files**. There is no longer a missing source archive blocker for the R315 compilation baseline.

## Real independent full clean source rebuild — PASSED

The archive's original `tools/rebuild_from_source.py` was executed in a newly created isolated private workspace with the entire exact `source/` tree, two hash-pinned dependency JARs and JDK21. Its invocation uses `javac --release 11 -proc:none -g:none`, an explicit empty sourcepath, and no original SpawnPK game-class binary fallback.

**Actual output, independently reproduced here:**

```
R311_PRIVATE_REBUILD_PASS classes=1386
sha256=b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721
```

That SHA matches `MANIFEST.json` exactly; the verified classfile count is **1,386**. This is a reproducible source compilation, **not** a claim that the bytecode equals the untouched original 17.5MB game client JAR (which contains 10,502 classes including bundled dependencies), or that the R315 source is original-author code.

The source itself remains partially deobfuscated: **307** files with a `Class<number>.java` basename, **894** files containing `field<number>` identifiers and **809** files containing `method<number>`.

## Readable source pass 1 — cleanly compiles as well

The R315 `rs/scriptpacket/Class260.java` owner is an abstract Guice `Module` with `handlePacket()`, `setPacket(Packet)`, `setClient(Client)`, packet readers, and no competing `AbstractScriptPacketHandler` file. A privately generated candidate renamed it to **`rs.scriptpacket.AbstractScriptPacketHandler`**, updating **144** lexical occurrences across **71** Java files and preserving all other Java text.

Running full `javac --release 11 -proc:none` against this **1,277-source renamed tree**, with the same two non-project dependencies, returned **exit 0 and 1,386 compiled classfiles**. The rename intentionally changes Java symbolic type names; the resulting classfile set is **not expected to retain R315's original JAR SHA**. Its equivalence under JVM class/member remapping, reflection strings, and original game runtime has **not** been established. The readable name is **inferred/review candidate**, not accepted original identity.

Remaining numeric source filenames: **306**. Method/field semantic naming and exact original-JAR verification are the next large work packages.

## Reproducible private workflow added in this PR

`scripts/prepare_v309_r315_complete_readable_source.py` accepts the **exact SHA-pinned R315 private archive**, verifies all 1,277 sources against two independent inner SHA maps, checks both dependency JAR hashes and refuses any `rs/` game-class fallback in those JARs. It stages only Java files and a private manifest into a *new* directory; it can preserve the `baseline` source or apply the narrow `readable` `Class260` rename. No original JAR or binary dependencies are written to this public source repository.

```powershell
py -3 scripts/prepare_v309_r315_complete_readable_source.py `
  --r315-archive "C:\private\SpawnPK-v309-R315-Full-Recovered-Source-Private.zip" `
  --mode readable `
  --new-private-output "C:\private\v309-r352-readable-source"
```

The archive and private output are intentionally absent from hosted CI: CI runs only **synthetic miniature ZIPs and fake dependency JARs**, checking SHA/casefold/traversal/symlink protection, exact source-set validation, no project-binary fallback, no overwriting and inherited R351 rename tests.

The owner has also been given independent private downloads: complete R315 source-only ZIP; complete source rebuild kit with pinned dependencies and build script; and source-only `readable` pass-1 ZIP with the precise inferred rename and build receipt. These files are not evidence of a certified Source-M1 public release.

## Next exact target

**Shift effort from restoring the tree to deobfuscating the complete buildable tree**, especially high-reference numeric class owners, related methods/fields and Java-safe package/type collisions. Every mapped class should be compiled from source with zero original-client binary fallback and checked against the original v309 JAR's corresponding symbolic JVM behavior. Preserve baseline source separately and never claim a candidate semantic rename is original author-provided.

Keep this PR **draft/unmerged** and stacked upon R351. No production v312, updater, original JAR/cache or live server behavior was modified.
