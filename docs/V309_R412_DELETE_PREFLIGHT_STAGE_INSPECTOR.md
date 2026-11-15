# R412 — pre-delete stage admission guard and non-destructive inspection

**Repository:** Trexzo/SpawnPK-Client  
**Stack:** R411 draft PR #1207  
**Status:** DRAFT / UNMERGED; no private client execution or authorized release.

## Goal and confirmed R411 gap

R411 rejects startup history load, saves, Clear all and legacy cleanup
when the history store observes an unresolved
\`loot-history.json.tmp\`. However, a confirmed source/type/individual
record deletion could still modify the Swing panel *before* its
synchronous \`persistHistory()\` attempted the R411 stage admission
check. After the store rejected the write, the plugin would mark
history unsafe and block automatic rewrites but would **not restore
the deleted visual row**. R412 narrows this known gap.

## Isolated owner-private R412 change (not published)

From a fresh isolated copy of the owner-private R411 source,
**only \`rs/plugins/loottracker/LootTrackerPlugin.java\` changes**.
Within \`r402ApplyPanelDeletion(Runnable mutation)\`, for persistent
confirmed edits, the code:

1. Checks current plugin/panel and Swing EDT ownership, retaining
   the preexisting UI-only behavior when \`rememberLoot()\` is false.
2. Acquires the original \`r401FileGate\`—the monitor also used by
   ordinary background autosaves and confirmed edits in this plugin.
3. **Before any history generation increments, transaction flags,
   panel mutations or disk writes**, calls
   \`historyStore.r411StageState()\`.
4. Only \`LootHistoryStore.R411StageState.CLEAR\` is admissible.
   If the stage is \`ORPHAN\` or \`UNSAFE\`, the operation sets
   \`r401ClearUnsafe=true\` and resets
   \`r396LastCommitSucceeded=false\` under \`r395HistoryGate\`,
   logs the refusal and **returns without invoking \`mutation\`**.
5. For an observed \`CLEAR\` state, the unchanged R402
   history-loaded/clear-in-progress/unsafe/handoff guards,
   synchronous deletion mutation, FileGate-held disk receipt,
   post-edit unsafe flag and transaction cleanup remain.

This protects against a **staging file that already exists when
the local deletion transaction reaches its FileGate admission
boundary**. It is not an interprocess filesystem lock. A different
process can create/replace a file after this metadata check;
the subsequent R411 save guard or R410 \`CREATE_NEW\` may still
refuse the write **after** a visible panel edit. The old unsafe
quarantine applies, but **complete failure rollback is not yet
implemented**.

The preflight does not introduce a new EDT hop, future, timer,
executor, stage reader, cleaner, cross-process mutex or file
delete. Confirmed deletion is still synchronous and can block the
EDT behind a concurrent background writer.

## Public read-only staging inspector

\`tools/r412/inspect_history_stage.py\` is an independently
written portable script for explicitly authorized directories.
It **requires** \`--directory\`; it does not search the machine or
guess the user's history folder. Its default is metadata-only and
it examines only two basenames in that directory:

- \`loot-history.json\`
- \`loot-history.json.tmp\`

It reports file **type and size**, presence of unexpected node types,
and one conservative stage classification:

| Observed stage | Classification | Action |
| --- | --- | --- |
| Missing path | \`CLEAR\` | No stage observed; does **not** prove the main file is authoritative |
| Regular file, including zero bytes or oversized file | \`ORPHAN\` | Refuse automatic recovery or cleanup |
| Directory, symlink, inaccessible, other nonregular path | \`UNSAFE\` | Refuse automatic recovery or cleanup |

With explicit \`--hash\`, the inspector may compute bounded SHA-256
for regular files up to \`--max-bytes\` (hard cap **64 MiB**).
It does so only where the platform exposes \`O_NOFOLLOW\`;
otherwise it reports \`UNAVAILABLE_NO_NOFOLLOW\` rather than
opening a path that might become a symlink between metadata
inspection and reading. Where supported, it checks file identity
and size/timestamps before, during and after reading to detect
some replacement races. **This does not guarantee stable
interprocess state**. File metadata can change immediately after
inspection, a malicious process may alter records, and SHA-256
here is neither an authenticated journal nor a proof of the
authoritative history image.

No recovered source, loot records, JSON payload, usernames,
absolute folder paths or private file contents are included in
its report. The inspector **never writes, deletes, renames,
repairs, quarantines by moving, or selects one version as newer**.

Examples using **only a user-created synthetic folder**:

\`\`\`powershell
python tools/r412/inspect_history_stage.py --directory C:\Temp\my-synthetic-history
python tools/r412/inspect_history_stage.py --directory C:\Temp\my-synthetic-history --hash
\`\`\`

These examples do not authorize inspecting any production history
file or connected user folder automatically.

## Verified owner Windows evidence

- Owner TEMP private isolated JDK21 \`javac --release 11\`
  build: **1,277 Java sources → 1,389 compiled classes PASS**.
- Exact byte comparison against R411 private candidate:
  **one Java source changed** (\`LootTrackerPlugin.java\`) and
  **one existing class changed** (\`LootTrackerPlugin.class\`).
  All other 1,276 source files and 1,388 classes byte-identical,
  including R411 nested staging-state enum.
- Independently SHA-pinned R381 source/JAR comparison retains
  the eight established modified Loot Tracker classes plus
  R411's one new enum. No additional class or source drift.
- Public-only SHA-pinned static verifier
  \`tools/r412/audit_delete_preadmission_guard.py\`
  executed against the actual owner-private prior and candidate
  source/class trees: **\`R412_PRIVATE_DELETE_PREADMISSION_STATIC_GATE_PASS\`**,
  exit 0. Verifies local FileGate placement, immediate stage
  refusal, preserved original admission guards, no UI mutation
  on refusal, original disk receipt path and byte scope.
- **52 Python invented tests** passed on owner Windows, with
  **three environment-dependent tests skipped** (real symlink
  creation and Linux-style \`O_NOFOLLOW\` availability).
  A negative test first exposed incomplete matching of the
  old clear/unsafe/handoff checks; the static verifier was
  tightened before final acceptance.
- **20/20 Java** standalone synthetic preflight scenarios
  passed locally. The model covers local writer contention,
  orphaned stage, missing/stopped session, UI-only operations,
  normal successive confirmed edits, failed disk receipt,
  foreign-process stage race, and old unsafe quarantine.
- Private custody-only owner TEMP archive:
  \`R412-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\` SHA-256
  \`8ceea4a1b3c57eeb6493863e4b4d8c6ccef8011a44d6af77301abac8c38978b9\`.
  It was compiled and packaged but **not launched, installed,
  uploaded, distributed or executed**.

## Remaining blockers

This is **pre-admission safety** and **manual inspection
observability**, not automatic recovery. There is no validated
process-independent stage owner, distributed lock, authenticated
before/after journal, safe cleanup selector or integrated R409
replay. The JSON writer still cannot prove a post-replacement
exception means the old file remained intact.

The inspector is informational; its report does **not authorize**
manual file deletion or production remediation. An orphan may
actually belong to an in-flight writer.

The EDT may still block while obtaining \`r401FileGate\` or
performing the synchronous write. A failure after a clean
precheck can still leave on-screen state different from disk.
Neither v309 original-client behavioral parity nor live v312
compatibility has been verified. No restricted guest runtime
acceptance or machine power-loss durability demonstration
exists. The root cause of the original client freeze is still
unproved.

## Next: R413

Build an independently verified staged-file transaction
recovery decision and/or identity-preserving UI rollback before
moving destructive confirmed edits off the EDT. In particular,
the post-preflight / pre-commit failure window must not be
reported as a successful deletion, and unknown disk bytes must
remain quarantined until deliberately reconciled.

**Keep R412 draft and unmerged; no private client launch,
production deployment, merge or distribution authorized.**
