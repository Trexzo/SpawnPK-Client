# R374 — atomic rename-intent staging and file-content flush boundaries

**Repository:** `Trexzo/SpawnPK-Client` · **Base:** R373 PR #1168 · **Release gate:** CLOSED (draft/unmerged; owner-private full source).

## Problem established by static source audit

In the recovered R373 `LoadoutStore.beginFolderRename`, `Files.writeString(receipt, ..., CREATE_NEW)` created the **final** `.loadout_rename-*.pending` path before its contents were fully written and forced. An interrupted/failed write could leave a malformed final receipt visible to the startup receipt scanner, which deliberately stops recovery on malformed receipts. R373 also atomically replaced staged folder and `order.settings` files without explicit `FileChannel.force(true)` for those staged file bytes. These were **potential interruption/durability gaps established by source audit**, not a reproduced physical power-loss event.

## Private R374 candidate — one recovered Java file changed

Exactly `rs/gui/loadouts/io/LoadoutStore.java` differs from R373 among 1,277 SHA-pinned sources.

1. `beginFolderRename` creates a uniquely named `.loadout_rename_stage-*.tmp`, outside the final `.loadout_rename-*.pending` scanner pattern; writes the full intent, forces the staged file, checks for a competing final receipt, then publishes with a same-directory `ATOMIC_MOVE` without a non-atomic fallback. It cleans up its temporary file on failure. It does not guess what to delete when published receipts are malformed.
2. `saveFolderWithLock` forces the staged loadout payload before writing a version receipt or replacing the destination.
3. `writeFolderOrderSettingsWithLock` forces the staged ordering file before atomic replacement. The R373 rename-order recovery path already forced its staged order file.

These improve **pre-commit file-content persistence**. They do not provide a guarantee that directory renames or deletions will survive a physical power cut, especially across operating systems. `FileChannel.force(true)` on a regular staged file does not itself synchronize the parent directory entry, make several renames atomic, eliminate noncooperative writer races, or prove version/order/rename receipt cross-file consistency.

## Verified private offline evidence

- New real-source-backed Java fixture: **32 assertions PASS**. Tests complete receipt publication; non-final, partially written stage-file isolation; collision/overlap refusal; source preservation; idempotent post-copy restart; malformed final receipts kept for review; held cooperative lock; normal folder and order saves. No original game launch or user cache.
- Inherited real-source-backed fixtures: **278 independent assertions PASS** (R373 45, R372 56, R371 16, R370 29, order.settings 28, store 44, serializer 60).
- Full JDK21 `javac --release 11`: **1,277 recovered Java sources → 1,388 classes**. Original full compile and clean independent kit extraction/rebuild produce **identical** JAR SHA-256 `ca0505f02b0a36ebfe9897b2de9da39dc2f0a2b6925d631a7ce22d735856a023`.
- SHA-pinned private source delta: R373 `c87c7e2158437f03c3f52e1d88f2c91a6e9949bedc9e74917b50d30186b67e67` → R374 `a8c7b3a044ce1ac106069bd935412edbaabff4546e3618df5810e54ccf924795` (one changed source).
- Public `scripts/verify_v309_r374_receipt_staging.py` and **24 synthetic Python tests** exercise fail-closed archive provenance only; hosted CI does not compile proprietary Java or prove private regression results.

## Explicitly unproven

**No physical power-cut test, parent-directory fsync proof, cross-file atomicity, uncooperative-writer guarantee, original-v309 JAR bytecode/runtime parity, actual GUI login/reconnect, v312 compatibility, or real user-cache testing.** The public PR includes only a verifier, synthetic tests, SHA witness, workflow, and this report; recovered Java, dependency binaries, and JAR remain in the private owner delivery. Keep **DRAFT / UNMERGED**. The production v312 installation/updater, original v309 JAR, live cache and game server were not modified.
