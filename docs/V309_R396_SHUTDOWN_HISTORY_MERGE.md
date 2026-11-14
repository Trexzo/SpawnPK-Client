# R396 — private shutdown merge for async loot restoration (experimental)

**Repository:** Trexzo/SpawnPK-Client. **Stack base:** R395 draft PR #1191.
**DRAFT, UNMERGED. Private-source release gate CLOSED.**

## Problem and engineering change

R395 prevented ordinary saves from overwriting disk history before an asynchronous
initial restore completed. But its plugin shutdown invalidated the restore
generation then returned with the save still deferred. Any live drops received
during that window could be lost on process exit even though the existing
history file was safely retained.

The R396 **owner-private** candidate changes only two files relative to the
golden R381 source kit:
\`rs/plugins/loottracker/LootTrackerPlugin.java\` and
\`rs/plugins/loottracker/LootHistoryStore.java\`.

- A separate pre-restore buffer holds the **identity and occurrence of each
  live drop** until a save reports completion; it is not cleared simply when
  an EDT drop callback consumes the original pending queue.
- On plugin shutdown while initial restore remains incomplete, the candidate
  invalidates pending asynchronous callbacks, strictly reads the existing
  on-disk history, merges the buffered live drops, and writes a new history
  through the existing staged atomic-replace path.
- \`LootHistoryStore.loadForMerge()\` distinguishes an unreadable/invalid
  history from a genuinely missing file; invalid records or unsupported
  formats cannot silently be interpreted as an empty history that may be
  overwritten. The legacy \`load()\` behavior remains available for other
  callers, while async restore also switches to the strict result.
- \`saveWithReceipt()\` returns success only after the existing
  \`AtomicFileReplace.move()\` completes without an exception. Existing
  \`save()\` call sites remain valid through a wrapper.
- When an original-file read or save fails, the original file is preserved
  and the candidate **does not claim completion**. The affected new drops
  remain only in volatile memory; their durability across process exit is
  **not guaranteed on failure**.
- On a successfully acknowledged shutdown save, the following plugin start
  may discard stale panel rows before reloading the now-saved disk history,
  avoiding a duplicate display. If no save succeeded, stale in-memory
  records are not deliberately cleared.
- User-triggered clear invalidates the old restore generation and the
  pre-restore record buffer to avoid resurrection.

**Tradeoff:** the shutdown fallback performs strict file read/parse and
staged write *synchronously* before returning. It can block the Swing event-
dispatch thread, especially for large histories (up to 64 MiB), so this
is not a complete UI-latency fix. It is an experimental prioritization of
recoverability when shutdown occurs mid-restoration.

## Verified isolated owner-Windows evidence

- R381 private source ZIP verified by original SHA-256
  \`902e3b583840073c095ea51c5fe5bee4034340ab92bd19dc7c36f3173f092f96\`.
- A second independent private candidate was created under
  \`R396-Private-Shutdown-Merge\` inside the owner's preexisting isolated
  TEMP workspace. The R395 candidate and source ZIP remain untouched.
- **1,277 Java sources compiled** successfully with owner Windows JDK21
  \`javac --release 11\`, yielding **1,388 .class files**.
- Comparison against R381 and R395 verified exactly **two changed
  compiled classes**: \`LootTrackerPlugin.class\` and
  \`LootHistoryStore.class\`. No unrelated compiled class changed.
- An R396 SHA-pinned public-safe read-only verifier inspects the original
  source kit, compiled reference JAR and isolated candidate source/class
  trees, checks exact two-file change scope and expected source structure,
  and emits **counts and fail-closed flags only**.
- Standalone, proprietary-source-free Java scheduling model:
  **13/13 tests passed** on owner Windows/JDK21. It covers stop before/after
  read, live drop queued/delivered, repeated identical drops, duplicate
  restore suppression, parse/write failure preservation, reenable/restart,
  clear invalidation, and regular steady-state shutdown.
- Public Python regressions additionally verify source and bytecode scope,
  strict-read and success-acknowledgment contracts, refusal to overwrite
  existing reports, and malformed/modified candidate negatives.

**No proprietary Java sources or JARs are committed to GitHub, uploaded to CI,
or included in this PR.** The private candidate has not been launched or
loaded in a game. The original v309 archive, live v312 installation,
friends' updater, caches, accounts and network settings remain unchanged.

## Nonclaims and remaining blockers

The public Java race model is NOT the recovered \`LootTrackerPlugin\`, and a
static source/class gate does not prove the private code's runtime races.
No disposable guest with independently verified network and writable-host
mount isolation has been established. No actual client/plugin GUI startup
is authorized or performed.

Still unproven: disk/atomic-rename durability after power loss, concurrent
writers (R378 lock-path existence is not lock ownership), full 64 MiB parse
latency, process termination mid-merge, disk-full/read failure persistence
of new drops, actual restart rehydration with the private GUI, original v309
behavioral parity, v312 compatibility, and real-world freeze remediation.

**Stop now rather than overwrite corrupt history** is intentional. Even after
the success-acknowledged merge, do not claim zero loss for every OS/storage
failure. All release/merge gates are FALSE. Keep DRAFT/UNMERGED.
