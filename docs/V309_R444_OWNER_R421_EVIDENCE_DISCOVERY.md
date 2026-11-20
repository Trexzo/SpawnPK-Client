# R444 — Discover earlier owner-TEMP R421 evidence without touching the client

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R443 draft PR #1239  
**Status:** DRAFT, UNMERGED, NOT DEPLOYED. Public read-only tooling only.

## Motivation and current access

R443 proved the historical R315 private import manifest contains a source inventory and dependency hash references but **cannot establish** the R421 source/class baseline. The current owner-private GitHub default branch also did not expose the needed R421 manifest. An owner-PC query found authorized device `DESKTOP-LTXXO4K` **offline** at R444 intake (last seen roughly five days earlier). There has been no owner-local R421 scan in this revision, and the absence of a prior approval cannot be inferred from the missing network connection.

## Implemented read-only owner-local discovery

`tools/r444/scan_owner_r421_artifacts.py` intentionally has a single explicit `--owner-read-only-evidence-audit` entrypoint and no ability to supply an arbitrary live-client path. It operates only in the current owner account's OS TEMP namespace, restricting enumeration to:

- The previously identified `SpawnPK-R386-Isolated-Acceptance/R421-Private-NoFollow-Cache-Directory-Preflight` workspace and similarly named historical R421 acceptance folders under the same isolated parent.
- Disposable `R424-Private-Candidate-R425-*` TEMP receipt folders.

The scanner **does not traverse** any original source tree, compiled classes or dependencies while searching candidate filenames. It independently counts regular `.java` and `.class` files in the two **exact expected** isolated R421 source/class roots and SHA-checks only the known pinned original `LootHistoryStore.java` and `LootHistoryStore.class` files. It never reads unrelated user directories, live client folders, loot history, game settings, deletion logs, journal markers or credentials.

Candidate filenames are matched only to bounded `R421`, `inventory`, `manifest`, `SHA`, `acceptance`, `baseline` or `receipt` metadata; no filenames or paths are printed. Up to 24 historical directories and 600 file/directory entries are inspected (depth at most four), and JSON candidate reads are capped at 4 MiB. Files/dirs must be regular, with symlink/junction refusal and no link following.

A candidate containing the R442 schema, the correct source/class counts, and the original pinned Store SHA identifiers is counted as a **possible R442 manifest shape only**. It is **not** authenticated, accepted, imported, auto-converted or upgraded into an approved reference. Existing R425 and R432 receipt filenames are counted; their mere presence **does not prove** a prior compile or assertion PASS.

The only stdout is a small JSON aggregate of found counts, expected file counts, and matching boolean Store SHA checks, plus permanent `possible_reference_sha_independently_approved=false`, `source_class_inventory_independently_approved=false`, `owner_private_compile_executed=false`, `release_authorized=false`, and `merge_authorized=false`. No raw private SHA256s, file paths, inventory lines or source bytes are exposed.

## Owner-side usage after Desktop Commander reconnects

From the `SpawnPK-Client` GitHub working checkout **at or after R444**, on the authorized owner PC in a PowerShell 5.1 terminal:

```powershell
python -B tools\r444\scan_owner_r421_artifacts.py --owner-read-only-evidence-audit
```

This writes **no file**, starts **no game or Java process**, and creates **no new TEMP candidate**. The output's metadata is safe to compare with the R442 admission requirements, but it does not create or approve an R421 manifest.

Do **not** run any client or R425/R432 compile based solely on R444. If a plausible historical JSON is located, retain it offline, establish an *independent* previously approved SHA256 and custody record, then run R442 verification and R440 read-only admission. R425/R432 actual-class and JVM tests remain a separate explicit owner-only gate. If only source files and class counts exist without a historical complete per-file inventory or independent approval, the blocker remains unresolved.

## Public verification scope

16 synthetic TEMP regressions exercise observed source/class counts and original Store pins, missing directories, malformed possible manifests, bogus R425/R432 receipts, unrelated path exclusion, symlink refusal, bounded directory and JSON file size limits, zero private paths/hashes in output, explicit CLI flag, and real Python subprocess exit. Windows/Ubuntu × Python 3.11/3.13 CI additionally runs inherited R443→R440 and R426 public-only suites. **The hosted CI uses invented files, never owner-local private files.**

The R415/R417 persistent deletion intent/ack markers and write fences remain intact, R424 `commit=false` remains hardcoded, and no live SpawnPK client/JAR/asset modification, loot-history deletion, journal removal, write unlocking, merge or deployment is permitted.

## Continued research direction

Recover any original R421 accepted source/class reference from prior historical owner archives rather than generating a passing expected hash from an unknown current tree. Distinguish metadata candidates, previously signed manifests, source/class compile assertions and physical v312 runtime acceptance; these are separate gates. Once owner-local evidence has actually been authenticated, move from this discovery tooling to R442→R440→R425→R432 private execution and then the R427–R431 actual asynchronous Store/Plugin integration.
