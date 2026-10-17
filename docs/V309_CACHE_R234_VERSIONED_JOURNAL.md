# Cache R234: versioned transaction journal and missing-witness safety

**Scope:** Lane B, `CacheUpdateTransaction.java` only; private v309 source donor, review-only public diff. Coordination: issue #1117.

## What changed

R233 writes an `.install-witness` (staged content fingerprint and original-cache presence). Its `readInstallWitness()` intentionally returns `null` for pre-R232 journals without this file. Unfortunately, if a NEW pending transaction loses its witness file, recovery also treats it as an old witnessless journal, weakening safeguards before deleting an uncommitted root or original backup.

R234 marks all **new** workspaces with `SPK-CACHE-TRANSACTION-V2`. From `STAGED` onward, including `PROMOTING`, `PROMOTED`, `ROLLBACK_EMPTY` and rollback states, missing or malformed installation witness fails **before any recovery mutation**. In `PREPARING`, the absence is allowed because that phase precedes witness creation. Existing V1 journals are accepted and remain V1 when recovery rewrites their state, retaining the compatibility contract.

**Boundary:** This is a missing-file/downgrade protection, NOT a signature or defence against an attacker with permission to rewrite the entire V2 journal into V1. Hardware crash consistency and the race with outside cache writers remain unproven.

## Exact private evidence

- R233 source preimage SHA-256: `5bd41aa1442642ce9b3ddc7a914cf0a98be98b6f3a85e763e7281b3dfe86aff6`.
- R234 source postimage SHA-256: `bc08aff2ddd3948f5ea8c248100234a39ee03cafd66b24e27b48c85e91aa2cad`.
- New source Git blob SHA-1: `10fb616668cd475b1170bebfd432f38547b8afd0`.
- `javac --release 11 -proc:none -g:none` full private compile PASS: **1,277** Java files, **1,388** classfiles, zero errors. Versus R233: only one Java source and one compiled classfile changed.
- **21/21 offline Java regression programs PASS** on Linux; new R234 versioned-journal suite **21 assertions PASS**. Inherited cross-process hard crash/lock, rollback, real cache extraction, HTTP downloader, ZIP and offline tests all PASS. The inherited R232 legacy test was adjusted only to create an explicit V1 journal before deleting its witness; R234 independently checks that deleting a witness from V2 is rejected.
- Full private bundle `SpawnPK_v309_R234_VERSIONED_JOURNAL_PRIVATE.zip` SHA-256 `b88fa9565d048aac56683a27056852f8af08c2bbdaf225a993315cf15da5f199`.
- Embedded changed-only ZIP SHA-256 `8c6f7d9cd06ac2f8cd5a263e70a9f91a6796fbbb190f8185206894eebd564762`.
- Full private source ZIP SHA-256 `57b900ea9788cfae52ab19efeafd62940ced7f195b11aeda9585da8b7bddcde3`.
- Compiled Java11 class-only JAR SHA-256 `a3a5e2eb8eacd052b27cd5ca2225070caff762fa0140ea86b006711e5c10593b`.
- Outer ZIP CRC and all nested source, class-only JAR and dependency SHA-256s passed; ZIP was built twice identically.

## Integration contract to Lane A

Only overlay `src/rs/cache/updater/assets/CacheUpdateTransaction.java` after Lane A has adopted R233, and only if its source matches the exact R233 preimage. The private R234 ZIP contains a PowerShell one-file overlay with SHA preflight, .bak and automatic rollback, full Java11 rebuild and 21 offline regressions. Preserve canonical Lane A `CacheUpdater.java`, downloader, GUI, networking, assets and launcher.

GitHub `tools/java/r234/R234_REVIEW_ONLY.diff` has blob `9aaba6976a176624cc9345cf39476eceacf553b0`, byte-for-byte identical to the private R233→R234 production diff. The full proprietary private client is not published, and this branch has **no hosted R234 Java11 CI or native Windows game acceptance**. Keep PR DRAFT.
