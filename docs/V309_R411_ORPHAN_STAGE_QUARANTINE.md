# R411 — orphaned history-stage quarantine at restart and destructive operations

**Repository:** Trexzo/SpawnPK-Client  
**Stack:** R410 draft PR #1206  
**Status:** DRAFT/UNMERGED; owner-private source/binary release CLOSED.

## Objective

R410's experimental history-only writer requires strict atomic replacement,
flushes and forces a new staging file before the rename, and uses
\`CREATE_NEW\` rather than overwriting an unexplained
\`loot-history.json.tmp\`. A leftover stage can mean a terminated or
failed write, an interrupted replace, or a still-active writer. Its
presence alone **does not prove it is abandoned**, and its age cannot
justify automatic deletion. R410 intentionally left such a stage
untouched, but the history reader and Clear all could still treat
the canonical history as if no unresolved staging existed.

R411 adds a **metadata-only, fail-closed stage admission guard**
to the owner-private experimental history store, without implementing
automatic recovery and without reading, repairing, renaming or
deleting a staging payload.

## Exact owner-private source change

Only \`rs/plugins/loottracker/LootHistoryStore.java\` is modified
relative to R410. A new nested \`R411StageState\` enum deliberately
adds **one** compiled class to the existing set:

- \`CLEAR\`: \`Files.readAttributes(..., BasicFileAttributes.class,
  LinkOption.NOFOLLOW_LINKS)\` throws \`NoSuchFileException\`,
  meaning the expected stage path was absent at that moment.
- \`ORPHAN\`: the stage path exists and its metadata identifies a
  regular file. This includes files containing incomplete or
  malformed serialized bytes; contents are **never opened**.
- \`UNSAFE\`: a stage path exists but is not a regular file
  (including directories or symbolic links), or its metadata
  could not be reliably inspected due to I/O or security failure.

The helper \`r411RefuseUnresolvedStage(operation)\` returns a
refusal unless the state is \`CLEAR\`, and logs the blocked
operation and staging state. It is invoked **before any substantive
work** by four existing history store methods:

1. **\`deleteStale()\`**: avoid destructive legacy-format cleanup
   when staging evidence is unresolved.
2. **\`loadForMerge()\`**: refuse background startup restoration
   and the shutdown merge by returning \`null\`. This prevents a
   main file from being incorrectly treated as authoritative
   while an unverified partial replacement exists, including when
   the main file is missing entirely.
3. **\`saveWithReceipt()\`**: refuse routine, shutdown and confirmed
   edit commits by returning \`false\`. R410's \`CREATE_NEW\`,
   staged-file force, and strict atomic-move boundary remain intact.
4. **\`clearWithReceipt()\`**: refuse to delete the canonical
   history while its stage remains unresolved, returning \`false\`.
   The existing plugin Clear all path then fails closed rather
   than clearing its panel as if disk deletion had succeeded.

The guard does **not** parse the temporary file, inspect its
timestamp, consult process owners, acquire a cross-process lock,
open or truncate it, guess which file is newest, or authorize any
automatic cleanup. It is not a durable intent/commit marker.

The price-cache writer and the existing legacy
\`AtomicFileReplace.move()\` method remain unchanged.

## Owner Windows private verification

- Exact isolated R410-to-R411 source clone: **1,277 Java sources**.
- Full JDK21 \`javac --release 11\` compile **PASS**:
  **1,277 source files → 1,389 class files**.
- Exhaustive byte/class comparison:
  **one modified Java source** \`LootHistoryStore.java\`,
  **one modified existing class** \`LootHistoryStore.class\`,
  and **one added nested enum class**
  \`LootHistoryStore$R411StageState.class\`.
  All other existing Java/class bytes match R410.
  The pinned R381 comparison retains the eight established
  changed Loot Tracker classes, plus the one new nested enum.
- The pinned public-safe read-only verifier
  \`tools/r411/audit_orphan_stage_quarantine.py\`
  checked the **actual owner-private** R410/R411 source and class
  corpora and the independently pinned R381 references.
  Result **\`R411_PRIVATE_ORPHAN_STAGE_STATIC_GATE_PASS\`**,
  exit 0.
- **40/40 Python** invented source/class/guard negative and
  positive tests passed. A verifier weakness was caught
  and fixed: an unrelated later \`return false\` can no longer
  hide an unsafe \`return true\` in the immediate stage-refusal
  branch.
- Standalone Java 11-compatible **21/21 mandatory** synthetic
  real-TEMP-filesystem checks passed, with five additional
  consecutive **21/21** runs. They cover normal absent stage,
  orphan regular files, nonregular paths, injected metadata
  I/O/security failures, stage-only startup without a main
  file, refused saves, refused Clear all, skipped legacy cleanup,
  \`CREATE_NEW\` racing another writer, and preserving stage
  evidence after atomic-replace refusal.
- Optional real-symlink creation was **unsupported in the
  connected owner Windows test environment**, so no local
  symlink-runtime PASS is claimed. The private static verifier
  enforces \`LinkOption.NOFOLLOW_LINKS\`. Hosted Linux may
  exercise the separate optional symlink scenario.
- Private custody-only owner TEMP JAR:
  \`R411-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\`,
  SHA256
  \`97b709fb646bc4ab248927391f886ae612be90dd7b13540ac35c73c7f7288a29\`.
  Compiled and packaged but **not launched, shared, uploaded,
  installed or distributed**.

## Remaining gaps — NOT fixed by R411

**There is no automatic orphan recovery.** This is a deliberate
non-destructive refusal policy. A leftover stage may block future
startup restoration and all new history saves indefinitely until
a separate verified recovery procedure determines the
authoritative history image. Do not use file age or the mere
existence of a lock path as proof that staged bytes can be deleted.

**Late orphan after loaded panel:** if the panel was already
loaded and a staging path later appears, the current
\`r402ApplyPanelDeletion\` can still mutate the on-screen
panel before \`persistHistory()\` receives the R411 refusal.
The existing plugin sets its unsafe flag on an unacknowledged
deletion, preventing automatic disk overwrite, but **it does
not roll back that visible UI mutation**. A later milestone
must add an explicit pre-mutation refusal and robust
failure/rollback semantics, rather than pretending the
delete succeeded.

**TOCTOU and interprocess writers:** a stage can appear or
disappear after the read-only metadata observation. In the
single-instance writer, the R410 \`CREATE_NEW\` and file gate
mitigate clobbering; there is no cross-process lock or
general all-writer transaction proof.

**R409 reconciliation remains separate research.** There is
no integrated commit-intent journal, before/after file hash,
restart replay, authenticated ownership of completed edits,
or safe recovery UI. R410's strict rename and stage file
force do not prove durability of directory metadata or
power-loss survival.

**Latency remains:** confirmed deletion, Clear all,
logout and shutdown still do synchronous I/O; the original
frozen-window root cause is not established. The program
has not been run in an independently verified isolated
restricted guest and no real client UI performance evidence
exists.

The user's live v312 installation, real history, accounts,
friends' packages and normal client runtime were untouched.

## R412 priority

Add a non-destructive **pre-mutation guard** to confirmed panel
deletions and design a bounded, read-only recovery inspection
tool for orphan staging evidence (size/type/hash of explicitly
approved synthetic test files first). Preserve the stage
without guessing whether another process still owns it.
Only after verified intent/commit reconciliation and a
controlled recovery choice should an actual cleanup or
asynchronous delete path be considered.

**R411 remains draft/unmerged. No private game launch,
production installation, merge or distribution authorized.**
