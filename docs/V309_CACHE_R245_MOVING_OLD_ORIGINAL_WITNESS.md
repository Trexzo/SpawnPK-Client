# Cache R245 — authenticate live original before MOVING_OLD cleanup

**Lane B scope:** exactly one production helper, `src/rs/cache/updater/assets/CacheUpdateTransaction.java`. Canonical Chat A client integration is separate.

## Reproduced bug and remedy

R244 V3 `MOVING_OLD` recovery had `previous/` absent and the live root present. This journal state occurs after writing an original-cache rollback witness, but *before* moving the original to `previous/`. Recovery took the live-root/old-not-moved branch and recursively deleted the staged update + journal **without comparing the live root to the saved original**. The new regression against actual R244 classes failed with `Unexpected recovery response: V3 changed refused=false`.

R245 requires a V3 `HAD_ORIGINAL` installation witness and matching persisted original-content rollback witness for this exact `MOVING_OLD` state, before any workspace cleanup. Missing original, missing/corrupt fingerprint, added file, externally rewritten live cache, or incorrect NO_ORIGINAL provenance fails closed, preserving surviving data and journal. Normal V3 recovery and genuine V1/V2 compatibility remain. This is not a race-free filesystem lock against third-party writers.

## Actual private acceptance

- Required R244 helper preimage SHA256: `78b2de68d0ea781cac34cc4139dbd6f1f26623429a465385ce9cabc732f8b8ed`
- Final R245 helper postimage SHA256: `d32012d42342b5888ff35b9025bb66270d9b95c3538275ec4843c79ae97cf1fa`
- Exact 1,359-byte review diff Git blob `765f2c252950a593b2a8611f31e486010b2d6fb4`
- Exact 4,478-byte 40-check regression Git blob `e13d6d3f6522481968b48b4e6ce3431bad844150`
- Full actual `javac --release 11 -proc:none -g:none`: **1,277 Java sources, 1,388 classfiles, zero errors**.
- Exactly one production source and its one compiled classfile changed. All other 1,276 Java files unchanged from R244.
- **32/32 offline Java regression programs PASS**, including new `R245_MOVING_OLD_ORIGINAL_WITNESS_PASS checks=40`, previous CacheUpdater/downloader/ZIP-safety, transaction crash/lock and Windows-path fixture compilation. Native Windows-only alias branch was not executed under Linux.

## Private SHA-guarded handoff

Complete deterministic `SpawnPK_v309_R245_MOVING_OLD_ORIGINAL_WITNESS_PRIVATE.zip` SHA256 **`2750f396f7660fe1b971e4c730e620c5e4fa473dad437f7de49fdb88f745ec62`**; 22,553,436 bytes and 67 ZIP entries. Built twice with identical hash, verified outer/inner ZIP CRC and hashes.

- Incremental R244→R245 one-file overlay ZIP SHA256 `5823ea65c58109979d0bd1ab6f7b56ce71158d61b868e730db99e9135e357f23`.
- Cumulative R234→R245 one-file overlay ZIP SHA256 `f6ae107e3a3a47698ffed0a9afaa3668715665d5a6db4c51e332bfc7cb44b0c0`.
- Full source ZIP SHA256 `338538b29116f85b493cb42ac0467dc048a74da478a51ce70df3465345c35f2d`.
- Compiled Java11-target class-only JAR SHA256 `709236774530582c800b2703e812fb3ec077975fc89df11220cb75f487b35e96`.

The 12 complete private donor snapshots R234 through R245 contain identical other **1,276** Java sources. For Chat A still on R234 use `R245_Apply_R234_CumulativeOverlay.ps1` ONLY if canonical helper SHA256 exactly `bc08aff2ddd3948f5ea8c248100234a39ee03cafd66b24e27b48c85e91aa2cad`. For R244 use `R245_Apply_CheckedOverlay.ps1` ONLY if the actual helper equals the R244 preimage above. Unknown preimage: **STOP**. Both scripts read the nested ZIP directly, back up the preimage and verify the new SHA; never replace the full canonical tree.

Following a one-file integration, **Chat A must rebuild and run its current canonical source, cache regressions and GUI/localhost tests**, preserving its shader, GUI, downloader, map loader, network and world-synchronization work. The public PR contains the exact review diff and independent regression source, **not** hosted full-private-source Java CI. Physical power-loss, native Windows gameplay and external-writer post-check races remain unverified. Keep draft and do not merge.
