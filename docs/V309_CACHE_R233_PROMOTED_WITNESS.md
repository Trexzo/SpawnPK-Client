# Cache R233 — verify PROMOTED content before releasing previous-cache backup

**Chat B, cache only.** This is a *private full-source donor* with a public, review-only one-file diff; it is not a fully integrated runtime change.

## Correctness issue

The R232 cache helper persists an installation witness, but the `PROMOTED` recovery path could delete `previous/` without comparing the live tree to its staged fingerprint. An unrelated writer could modify the new cache after promotion, leaving the updater to discard the last known-good copy.

Cache R233 validates the persisted installation witness at three cleanup boundaries: after recording `PROMOTED`, when recovering with both the active root and `previous/`, and when recovering `PROMOTED` without `previous/`. On mismatch it rejects cleanup and retains the live cache and any existing backup and journal. Older witnessless journals remain readable but cannot be authenticated.

## Verifiable private acceptance

- Exact R232 source preimage SHA-256: `a7f823d22ac3b0a97c97d5fba27193d2ae4a39fd1ce9b02a9127edb1bf7a8e79`.
- Exact R233 source postimage SHA-256: `5bd41aa1442642ce9b3ddc7a914cf0a98be98b6f3a85e763e7281b3dfe86aff6`.
- Exact R233 source Git blob SHA-1: `ac8243d237401a2f07df9534bfc0960aa893d1a9`.
- Full Java 11 target build: 1,277 private Java sources, 1,388 compiled classfiles, zero compiler errors.
- Exactly one source and one classfile changed from R232; 1,387 classfile SHA-256s unchanged.
- 20/20 offline Java regression programs passed; new R233 program 22 checks passed including same-size/mtime tampering, unexpected and missing files, first installation, legacy witnessless replay and in-process post-promotion mutation.
- Native Windows game, actual power loss and R233-hosted CI **not verified**.

## Private handoff

Complete R233 bundle SHA-256: `21bd15e91c93343b3dc4fd9f41154c91ca08d9c24fa24f88900b8568ffa25b68`.
Internal changed-only ZIP SHA-256: `b87be049c721e402ec6136fd2110e4efa9ceb505ab51ef0ea010a591423d93bc`.

Only overlay `src/rs/cache/updater/assets/CacheUpdateTransaction.java`, and **only** on the exact R232 preimage. Lane A currently tracks the R231-integrated R239 source, so it must first integrate R232. Preserve all other canonical client source. The enclosed checksum-guarded PowerShell installer saves a .bak and refuses unknown hashes.

## GitHub status

`tools/java/r233/R233_REVIEW_ONLY.diff` is **byte-for-byte identical** to the private R232→R233 diff (Git blob SHA-1 `9b1786a87d7a04bb6cc8cff3a99e3698b04c6653`). Attempts to publish the full original-independent R232/R233 helper were blocked; do not claim that this PR's public branch compiles the R233 helper or passes hosted R233 tests. The private source is in the checksum-verified handoff ZIP.
