# R443 — R315 → R421 original-source inventory reconciliation

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R442 draft PR #1238  
**State:** DRAFT, UNMERGED, PUBLIC TOOLS ONLY; owner-private release remains CLOSED.

## Real historical evidence and its limit

A private **R315 import manifest**, archived October 29, 2026, is retained in the owner's ChatGPT file library. Its record states 1,277 original Java sources and individually recorded source-file SHA256s, alongside two dependency JAR SHA256s. R315's original `LootHistoryStore.java` file SHA differs from the independently pinned **R421** Store Java SHA recorded in R424/R425. The R315 JSON contains **no complete compiled-class SHA inventory**. Therefore it cannot be used to reconstruct the R421 compiled 1,394-class baseline, nor can it be accepted as the R442 historical R421 manifest.

The owner-connected **private GitHub repository's current default tree**, inspected read-only, contained no named R421 inventory or R421-specific reference file in the tree. No R421-specific branch was found by branch search. This is *not* a claim about uninspected owner-PC files, private repository history, older branches, archives or backups. The actual R421 snapshot remains an owner-local evidence blocker. **Do not publish the R315 file, its original source hashes, or its per-path source map in this public repository.**

## R443 diagnostic (never an admission gate)

`tools/r443/compare_r315_r421_references.py` accepts:

- `--r315-manifest` and **separately approved** `--approved-r315-manifest-sha256`, referring to an old complete R315 import JSON with source-file entries, sizes, import classification, and dependency hashes.
- Optionally, `--r421-manifest` and the paired, separately approved `--approved-r421-manifest-sha256` referring to the **full R442-formatted** R421 source-and-class manifest.

The program reads only those files. Both manifests must be regular, nonlink, bounded (≤4 MiB), UTF-8 JSON and byte-for-byte matched against their independently supplied approved SHA256 references. Duplicate JSON keys, unsafe relative paths, casefold collisions, incorrect 1,277-source count, malformed record hashes/sizes, missing Store or dependency records and an unverified R421 full-class manifest refuse the comparison.

If only R315 is independently verified, it returns `R443_R315_ONLY_R421_REFERENCE_STILL_MISSING` with source count, a boolean whether its Store SHA equals the R421 pin, and **no release or build approval**. If a valid independently verified R421 manifest is also present, R443 emits only **aggregate source-path counts** for unchanged, changed, added and removed Java files, whether the two dependency JAR hash pairs match, and whether the R421 class-inventory count is 1,394. No private source paths, raw per-file hashes, Java bytes, local private paths, or actual loot-history data are emitted.

Critically: R315 lacked a class-file inventory, so R443 **never** claims an R315→R421 compiled-class diff; a source diff cannot substitute for the R421 compiled baseline or for proving the two manifests' independent custody. Its output always includes `ready_for_private_compile=false`, `owner_private_r425_r432_executed=false`, `release_authorized=false`, and `merge_authorized=false`. R442→R440→R425→R432 alone controls potential owner-private acceptance.

## Owner-private evidence still required

1. Identify a **preexisting independent R421 archive or receipt** containing all 1,277 Java source paths and 1,394 corresponding compiled class paths, each with its own SHA256, plus R239_filtered.jar and R218.jar identities. The source Store and Store.class must match the original R421 exact SHA pins.
2. Independently review both historical records and approve raw manifest SHA256 references out of band. **Never derive a trusted reference hash from the potentially modified current file.**
3. Only on an isolated owner PC, optionally run R443 against both independently reviewed manifests to inspect aggregate source transitions. R443 does not modify source, launch a game, or compile anything.
4. Separately invoke the R442 manifest verification and R440 read-only gate, then—**with explicit owner approval**—the R425 private compile/39+ actual Store assertions and R432 73+ actual Store assertions/17 cross-JVM checks. Only then investigate the actual R427–R431 asynchronous Store/Plugin adapter and real Swing/v312 lifecycle acceptance.

There is no fully approved, current R421 original private source/class inventory available to this hosted execution, so those real gates **remain unexecuted**. The current GitHub PR adds only public Python verification logic, invented test fixture JSON and CI configuration.

## Public CI

Sixteen fabricated tests validate R315-only diagnostic status, aggregate source change counts, same-count path swaps, dependency mismatch, refusal of nonapproved R315/R421 digests, source traversal/case collisions/duplicate JSON, missing Store/dependencies, and a **real subprocess run** comparing synthetic full 1,277-source and 1,394-class snapshots. Windows/Ubuntu × Python 3.11/3.13 CI also runs inherited R442/R441/R440/R432/R426 public suites.

Keep R415/R417 persisted journal, deletion intent and post-delete write fences untouched; R424 hard-coded no-delete `commit=false`, R425/R432 nondeployment checks and release authorization flags remain unchanged. No merge, deletion, client JAR install, source distribution or write unlock is authorized.
