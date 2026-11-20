# R442 — Existing independently approved R421 inventory manifest admission

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R441 draft PR #1237  
**Status:** DRAFT / UNMERGED / PUBLIC TESTS ONLY. No owner-private R421 data or installed v312 game touched.

## Why R441 alone is insufficient

R441 correctly requires two separately approved SHA256 fingerprints covering all original **1,277 Java sources** and **1,394 classes**. The R440 wrapper already demands two approved dependency JAR hashes. But it previously accepted four manually typed hex values, and no checked-in evidence shows how those four values were tied to one independently preserved historical R421 source/class inventory. A caller could mistakenly generate all four fingerprints from current, potentially altered files and pass them as if they were approved.

R442 introduces a **single previously approved reference-manifest file** with one **out-of-band approved SHA256** of the complete manifest bytes. The verifier derives the exact R441 source/class fingerprints and existing dependency A/B SHA pins from that file. It **does not accept a new hash automatically calculated from the same current file as independent approval**.

## Expected private reference format

The file is UTF-8 JSON (maximum 4 MiB), with exactly five top-level keys:

```json
{
  "schema": "SpawnPK-R442-previously-reviewed-R421-inventory-v1",
  "archive_id": "R421-PreviouslyReviewed-Archive-Example",
  "source_inventory": {
    "rs/plugins/loottracker/LootHistoryStore.java": "<the already pinned original R421 SHA256>",
    "rs/example/Other.java": "<sha256 of that earlier archived file>"
  },
  "class_inventory": {
    "rs/plugins/loottracker/LootHistoryStore.class": "<the already pinned original R421 class SHA256>",
    "rs/example/Other.class": "<sha256 of that earlier compiled class>"
  },
  "dependency_sha256": {
    "R239_filtered.jar": "<previously approved SHA256>",
    "R218.jar": "<previously approved SHA256>"
  }
}
```

The above JSON is **illustrative and incomplete**. A real manifest must list **every one** of the 1,277 Java and 1,394 class paths with SHA256 for their exact archived byte contents, including the original R421 Store source/class exact hashes that are already hardcoded in R425. Only the two existing R421 dependency JAR identities are admitted. Paths use relative POSIX slash syntax; duplicate keys, casefold collisions, traversal, abnormal or missing records, unknown fields, and truncated/unexpected JSON are refused.

The `archive_id` is simply a human-readable reference label; it is **not** proof of timestamp, ownership, review, authenticity, or preservation.

## Independent owner-side approval requirement

A human must locate the **previously preserved, independently reviewed R421** manifest/archive and separately authenticate its origin and file list. The expected SHA256 of the full JSON file must come from that older approved custody record or be reviewed against the trusted archive out of band—not from the current unverified manifest under test. If no such historical evidence exists, **the real R442 gate cannot pass legitimately**. Creating a new manifest/hash pair from the current R421 directory would prove only that the current files match themselves, and would defeat the purpose. Do not upload private source, class files, dependencies, the manifest, or user history to GitHub.

The user-facing PowerShell entrypoint requires `-ApprovedR421ManifestPath` and `-ApprovedR421ManifestSha256` for both `-AuditOnly` and `-RunOwnerPrivateAcceptance`. The four older `-ApprovedDependencyASha256`, `-ApprovedDependencyBSha256`, `-ApprovedSourceInventorySha256`, `-ApprovedClassInventorySha256` parameters remain only as optional compatibility **cross-checks**; any supplied value conflicting with the verified reference is rejected.

Example only after independent reference approval (replace placeholders, do not invent):

```powershell
$entry = 'tools\r425\owner_only_run_r425.ps1'
$manifest = 'D:\TrustedOfflineArchive\R421-approved-inventory.json'
$approvedManifestSha = '<64 lowercase hexadecimal characters from separately approved custody record>'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $entry -AuditOnly -ApprovedR421ManifestPath $manifest -ApprovedR421ManifestSha256 $approvedManifestSha
```

**Do not run the full compilation flag unless the actual audit and separate review succeed.** R440 enforces the resulting four pins against present-day private files; R425 and R432 require the same full-tree digests again during compile and cross-process testing.

## Verifier implementation and trust limits

`tools/r442/verify_prior_r421_manifest.py` is read-only. It:

- Requires a regular, nonlink reference JSON file, bounded to 4 MiB; hashes the **raw bytes first**, before JSON parsing.
- Requires one 64-character lowercase **separately approved** raw SHA256, rather than a self-derived trusted reference.
- Rejects duplicate JSON keys and invalid UTF-8/JSON, unknown schemas, bad file paths, casefold collisions, missing original pinned Store source/class, changed inventory counts, invalid per-file SHA digests and missing/identical dependency values.
- Computes the R441 v1 deterministic full source/class fingerprints from the previously approved per-file mappings, and returns only their hashes, the two dependency pins, totals and explicit `release_authorized:false`. It does not print private filenames, source, JAR bytes or the manifest's path.
- Explicitly returns `reference_origin_independently_verified:false`; the tool checks file integrity against the supplied expected SHA **but cannot establish where that expected SHA came from**.

The PowerShell wrapper first validates the manifest and receipt, then validates current dependency hashes, then runs R440's read-only original Store/inventory audit. The candidate creation and R425→R432 gates remain behind `-RunOwnerPrivateAcceptance`. All deletion, deployment, journal cleanup and write-admission controls remain unchanged.

## Public CI and release hold

Sixteen new regressions use **invented** baseline maps, including a real Python subprocess processing a large fabricated 1,277-source/1,394-class manifest. The Windows/Ubuntu × Python 3.11/3.13 matrix also executes inherited R441, R440, R432 and R426 public-only checks, with PowerShell parsing on Windows. Hosted CI does **not** possess a legitimately approved historical manifest or any private Store classes; a green result is not a real R421 admission.

Outstanding: find and independently approve an actual prior R421 manifest/archive, run owner-local R442→R440 `-AuditOnly`, then separately run R425 and R432 real class tests. Only after those steps may the proposed R427–R431 asynchronous Store/Plugin integration and Swing/v312 testing be considered. Keep all PRs DRAFT/UNMERGED; no JAR install, history write, deletion, lock takeover, intent/ack marker removal, release or merge authorized.
