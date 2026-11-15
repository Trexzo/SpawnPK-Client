# R417 — restart acknowledgment model and ack-only admission fence

**Repository:** Trexzo/SpawnPK-Client
**Base:** R416 draft PR #1212
**Status:** DRAFT / UNMERGED; no private release, live game launch or automatic cleanup permitted.

## Why R417 is needed

R415 can record a confirmed-delete v1 intent and then replace the canonical history. R416 can passively validate that the committed image has a matching SHA-256 and canonical schema. Neither stage adopts history, acknowledges restart processing, or cleans up the unresolved intent. It would be unsafe to treat the mere presence of a valid-looking acknowledgment sidecar as permission to write again. Worse, if an intent disappears but an acknowledgment sidecar remains, the earlier R411/R414 admission path would not recognize that sidecar by itself.

## Owner-private code — narrow isolated R416 successor

A new owner-TEMP R417 source copy changes **only rs/plugins/loottracker/LootHistoryStore.java**. The R411 admission routine now invokes r417UnresolvedAckEvidence before the existing R414 intent classifier. This helper uses NOFOLLOW_LINKS metadata-only checks for both:

- loot-history.delete.ack
- loot-history.delete.ack.tmp

If either name exists in any form, or its presence cannot be checked safely, admissions return UNSAFE. This holds even if the original intent marker is absent. The previous history-restore, save, clear-all and legacy-cleanup paths already rely on the R411 gate. No marker bytes are opened and no files are removed, renamed or rewritten by the new helper. No actual acknowledgment producer or adoption pathway is wired into the private client.

### Actual owner Windows evidence

- JDK21 javac --release 11: **1,277 private source files → 1,393 compiled classes PASS**.
- Exact source delta R416→R417: **one modified source** (LootHistoryStore.java).
- Exact class delta R416→R417: **one modified existing LootHistoryStore.class**; no added, removed or other altered classes.
- Read-only SHA-pinned gate tools/r417/audit_private_ack_fence.py executed against actual isolated owner source/class trees: **R417_PRIVATE_ACK_SIDECAR_ADMISSION_GATE_PASS**, exit 0.
- The audit explicitly checks both exact sidecar names, first-position admission ordering and the absence of cleanup/mutation APIs in the new guard.
- No client JAR built for release, no recovered private code/classes/loot/player history uploaded, no actual game process executed, and no production v312/history touched.

## Public standalone synthetic crash research

tools/r417/restart_ack_model.py is an **invented Python TEMP-filesystem model** of a future acknowledgment design, **not** a port of recovered source. It uses a separately staged acknowledgment file, fsync, CREATE_NEW, a no-clobber hard-link publication step and an immutable digest/serial/nonce match against synthetic intent/history. It never deletes the original intent, restores real records or unblocks normal history writes. The modeled manual-adoption flag is only a contract placeholder, not evidence that adoption has occurred in the actual client.

44 synthetic restart scenarios test interruption after acknowledgment-temp fsync, after hard-link publication, after temp removal, corrupt/aborted images, changed markers, conflict/collision evidence, stale snapshots, symlinks and child-process restart. A separate 22-case synthetic gate suite includes negative controls for source/class scope, both exact marker names and prohibited cleanup APIs.

- **Owner Windows local: 66 tests, 63 passed, 3 optional symlink checks skipped, 0 failed.**
- First verifier revision had one false-positive source check (the .tmp name satisfied a substring test for the final name); an independent negative control found it. The checker now requires both distinct, exactly quoted names, and the complete suite was rerun green.
- GitHub Windows/Ubuntu × Python 3.11/3.13 CI is separate, and hosted results must be checked on the final head commit.

## Release blockers

This phase does **not** establish a safe production acknowledgment or adoption flow. The synthetic helper does not authenticate markers, acquire an interprocess writer lock, force parent-directory metadata, provide a power-loss guarantee, or prevent an uncooperative second client from rewriting history between observations. **Even a valid acknowledgment retains all write fences.**

R415 confirmed deletes still perform blocking disk I/O on Swing EDT. No private-game runtime tests, verified restricted guest, current-v312 acceptance, real history read/write, integrated crash after UI restoration, or original client freeze root-cause verification has been completed.

Keep this PR **draft/unmerged** and do not deploy or distribute a private build.

**Next: R418** — design and test a cooperative single-writer ownership/epoch protocol, immutable restart-adoption receipt and UI reconciliation, before considering any marker cleanup or re-enabling writes.
