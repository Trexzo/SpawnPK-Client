# Cache R239 — preserve modified original backup after promotion

**Lane B, source-only**; shared coordination in issue #1117.

## Reproduced defect and actual fix

R238 could return success while deleting `previous/` after a non-cooperating writer modified that old cache after promotion. The old staged-install fingerprint validated the new live cache but did **not** validate the original backup about to be discarded.

R239 writes a durable original-content fingerprint **before the original directory is moved**, using the existing rollback-witness format. NEW transactions use `SPK-CACHE-TRANSACTION-V3`, so older V1/V2 journals remain distinguishable. On a completed update and `PROMOTED` restart recovery, the helper verifies the original backup before releasing it. In case of mismatch, it preserves the altered old data, new live cache and recovery journal and reports failure. Interrupted V3 rollback also fails closed rather than silently accepting a substituted old backup. Real physical power loss and arbitrary writes after the last check remain unverified.

## Exact private donor

- **Only production source changed:** `src/rs/cache/updater/assets/CacheUpdateTransaction.java`.
- **R238 preimage SHA256:** `7754fb28fe5573f1ee733033a10d42c4d36722c9d4d4eb6530066d9d6f01c1be`.
- **R239 postimage SHA256:** `c7ab5f926fe7a73e36f5ecd133270132767755f4d4a40c92422ee803ede77689`.
- **Review diff** `tools/java/r239/R239_SOURCE_REVIEW.diff`: 7,175 bytes, Git blob SHA1 `a2afafd77c4636c4fc5d03068fa9c10ca0f92991`, verified exact against the private full-source comparison. This is a **review diff**, not complete public R239 helper code.
- All **1,277 private Java sources** compiled with `javac --release 11`: **1,388 classfiles, zero errors**. Only CacheUpdateTransaction.java/.class changed from R238. Other 1,276 sources and 1,387 classfiles identical.
- **26/26 executable offline regression programs passed**, including new `R239_COMMITTED_ORIGINAL_BACKUP_PASS checks=31`. Scenarios include afterPromotion same-size/unchanged-mtime backup mutation, repeat recovery, crash at promotion, missing witness, successful updates, initial install and V2 PROMOTED legacy compatibility.
- Five historical regression fixture sources were adapted **only for testing**: four expect new journals to be V3 rather than V2; the R226 updated policy expects changed original data to be preserved under previous/ instead of automatically restored and cleaned. Original fixtures and adapted fixtures both included in private package. No other production Java edits.
- Native Windows game and hosted R239 helper Java CI have **not** passed.

## Verified private handoff

`SpawnPK_v309_R239_ORIGINAL_BACKUP_WITNESS_PRIVATE.zip` SHA256 **`de80a84a932bc3f6a43b1d34b9c1142fb397ada03576222eaca4b9a4ce1510fa`**.

Inside the single package:
- `R239_CHANGED_ONLY.zip` SHA256 `3d4b091eb675cc70a92823b748a73ca3635bc49719387298b821b74307bf1e97`.
- `R239_COMPLETE_SOURCE_PRIVATE.zip` SHA256 `d8c975a4494076c61578a9dac1bfc1a6f4d14ea5aeb80b79cfbd8091eb6df555`.
- `R239_SOURCE_BUILT_PRIVATE.jar` SHA256 `bfa40f6e1d1af5aa1a646e9942b7b78f5e1129d904822eb254f358a8ed6f8aea`.
- SHA-guarded PowerShell changed-only overlay, R238 source backup, Windows full rebuild and all 26 regression scripts, tests and validation JSON. ZIP CRC, nested SHA256 and deterministic rebuild verified.

## Ownership and remaining acceptance

Lane A's canonical client **R242**, last checked, includes cache R234. Apply donor overlays **R235 → R236 → R237 → R238 → R239** in that order, verifying each preimage SHA and rebuilding the actual integrated private source. Do not overwrite Lane A's newer GUI, downloader, CacheUpdater, assets, local authentication or launcher by replacing its source tree.

The public PR is **review-only** and does not compile private game Java. No native Windows client, authenticated gameplay, post-comparison race freedom, or physical power-loss verification is claimed. Keep draft.
