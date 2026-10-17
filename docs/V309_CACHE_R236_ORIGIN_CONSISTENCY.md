# Cache R236 — V2 provenance and completed-transaction staging consistency

**Ownership:** Chat B, only cache transaction source. Shared coordination: issue #1117. Draft stacked upon the review-only R235 branch.

## Reproducible failure modes

An R235 V2 journal marked `PROMOTED` and holding `previous/` could carry an installation witness that falsely says `NO_ORIGINAL`. Because `PROMOTED` checks only the staged-content hash, that contradiction could still allow removal of the old backup. Likewise, a supposedly completed `PROMOTED` workspace with a recreated `staged/` subtree could delete that unexpected data during cleanup.

R236 validates V2 origin-state consistency before recovery acts: if `previous/` exists or if the state is `ROLLBACK_PREPARED`/`ROLLBACK_RESTORED`, the installation witness must say `HAD_ORIGINAL`. A `PROMOTED` transaction must no longer have `staged/`. Missing, malformed or contradictory V2 metadata rejects with IOException before mutating the backup or active cache. V1 historical compatibility remains.

## Exact private full-source acceptance

- **Changed source only:** `src/rs/cache/updater/assets/CacheUpdateTransaction.java`.
- Required R235 preimage SHA256: `39ae628442d65e6813f85322d126356f3e8bc1dc8d881c5a7a4247a6ff430d0a`.
- R236 source postimage SHA256: `d63d0cc78f27af4452307646c098cd35ceac2584283f0f612b862cd18a306b72`.
- Complete Java11 target `javac --release 11`: **1,277 real Java sources, 1,388 production classes, zero errors**.
- Exactly one Java source and one classfile differ from R235; 1,276 other Java files and 1,387 other classfiles identical.
- **23/23 offline regression programs passed**; new R236 state-consistency suite **48 checks**, including V2 NO_ORIGINAL contradiction with live old backup, extra stage in committed old/new installation, contradictory prepared/restored rollback, malformed PREPARING with unexpected backup, valid cleanup, and historical V1.
- Inherited cases include separate JVM crash/lock, cache extractor, archive traversal, HTTP downloader, and rollback replay. Windows-only alias assertion branch was skipped on Linux.

## Private artifact and integration

Complete `SpawnPK_v309_R236_ORIGIN_CONSISTENCY_PRIVATE.zip` SHA256 `374ea0ef81da56fa82b6eb9f247e53bb08ff8ccb2133c533d8a4f6bad91b8ad0`.
Embedded changed-only `R236_CHANGED_ONLY.zip` SHA256 `24d70a00852505fc2f028d780ab01852134793c1170e06844f841101807eba34`.
Complete Java source ZIP SHA256 `f1a02968dd65e4382b9c8771066bd92f61005a849a8e98fd79354b5988461b19`.
Production class-only Java JAR SHA256 `1dad15021b5f919d4ba915ac0da52e254bab3bad4596c295a63c2961ecf51bba`.

The reviewed 1,691-byte R235-to-R236 diff at `tools/java/r236/R236_SOURCE_REVIEW.diff` has exact Git blob SHA `bad212a10d1f07a876d0eeeb4b5e4db942262ae4`, byte-identical to private source diff. The public branch is a **review-only patch, not hosted full helper CI**.

Lane A currently R242 has R234 integrated. Integrate R235 and R236 sequentially as ONE source file each with SHA preflight; **never overwrite** Lane A's full source, CacheUpdater, downloader, assets, launcher, GUI or login work. Rebuild the actual integrated source and rerun graphical and cache acceptance.

**Not verified:** native Windows private game runtime, physical hardware power failure, malicious editing of both journal and witness, external writers after final comparison, full game source parity. Keep PR draft.
