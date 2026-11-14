# R403 — coalesced background worker for routine Loot Tracker autosaves

**Repository:** Trexzo/SpawnPK-Client.
**Stack base:** R402 draft PR #1198.
**Status:** DRAFT/UNMERGED. Private runtime launch and source-release gates CLOSED.

## Narrow source-backed problem

R402 fixed the known panel-deletion and clear/save ordering races but
synchronous persistence remained in the normal \`requestSave()\` and
\`onGameTick()\` paths. A chat/UI/loot event could reach \`requestSave()\`
from the Swing EDT, while the game tick normally runs on the client
thread. Both paths could synchronously serialize a large loot history
and write the file, blocking user interaction or packet processing.

Moving **every** save to a worker would be unsafe. A confirmed panel
delete needs the receipt before claiming success; plugin shutdown and
logout still need immediate best-effort persistence before loss of the
session. Therefore R403 is a bounded, conservative change to **only
routine autosaves**, not a full asynchronous persistence redesign.

## Actual owner-private R403 candidate

A new disposable isolated copy of the R402 owner-private reconstructed
sources was created under the existing TEMP acceptance workspace. Only
\`rs/plugins/loottracker/LootTrackerPlugin.java\` was modified.

- A per-plugin **single-threaded daemon executor** is created for each
  startup. Normal \`requestSave()\` and due \`onGameTick()\` saves now
  submit to \`r403QueueAutosave()\` instead of invoking the
  synchronous persistence method.
- If a worker is queued or writing, requests only mark one dirty
  follow-up; at most one autosave task is outstanding per plugin
  session. The normal interval and \`savePending\` throttle remain.
- A worker captures the issuing plugin-session epoch, checks active
  admission before running and passes that token via a ThreadLocal
  into the existing persistence method. **Both** the disk-write guard
  (under \`r401FileGate\`) and the post-write acknowledgement check
  reject an earlier-session worker.
- A missing, failed or not-fully-caught-up write receipt leaves the
  routine save pending for a later tick. Queued tasks remove their
  thread-local token and clear their coalescing flag in \`finally\`;
  cleanup checks the same epoch so an old worker cannot clear a new
  session's queue state.
- Shutdown closes drop admission and increments the epoch before
  retiring the worker with noninterrupting \`shutdown()\`. It keeps
  the R396/R401 synchronous final persistence path; it does not call
  \`shutdownNow()\` or wait on an executor while holding an event
  thread lock. Queued obsolete jobs are rejected by the epoch check.

**Not offloaded:** direct \`persistHistory()\` from logout/game-state
changes, \`rememberLoot\` enablement, restoration callbacks, confirmed
panel deletion, and synchronous shutdown. These remain subject to
existing latency. Deletion may still wait on an in-progress worker's
file-gate lock; that is a known UI-blocking limit.

## Actual owner Windows verification

- Full Windows JDK21 \`javac --release 11\`:
  **1,277 private Java sources → 1,388 classes** (exit 0).
- Exhaustive class byte comparison vs R402: **only**
  \`rs/plugins/loottracker/LootTrackerPlugin.class\` changed.
  Compared with pinned R381, the same three Loot Tracker classes
  previously established by R402 differ.
- SHA-pinned read-only public-safe static source/class verifier run
  on the *actual* owner-private candidate:
  **\`R403_PRIVATE_COALESCED_AUTOSAVE_STATIC_GATE_PASS\`**, exit 0.
  It verifies exact one-source/one-class delta, daemon/single-worker
  construction, coalescing, retirement, write/ack epoch fencing and
  preservation of synchronous deletion/logout contracts.
- **25/25 Python public synthetic negative/positive tests passed**
  locally; **15/15 standalone Java synthetic worker scenarios passed**
  locally, including blocked-writer submission, burst coalescing,
  restart retirement, stale worker rejection, failed write retries
  and a direct synchronized delete.
- Private archive for offline custody only:
  \`R403-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\`
  SHA256
  \`25d3c876b4a5d25b941abccdba6ac356bafc569e335987e4ea7f9cea30b91526\`.
  It was **not launched, installed, uploaded, distributed or shared**.

## Not established; next research tasks

This source-scope improvement does not prove actual live client
latency or CPU benefits. The worker still executes the existing
history serialization and atomic-file replacement code. Mutable
\`LootTrackerItem\` names/prices are updated from other Swing tasks,
and these value changes have not yet been given a complete
cross-thread snapshot transaction.

The worker's daemon nature means an abrupt JVM termination can still
lose a coalesced unsaved autosave. Logout and shutdown retain their
existing synchronous save attempt, but neither guarantees power-loss
durability. The R397 CRC journal is still a separate synthetic
prototype, not integrated. No global cross-process writer lock,
persistent event identities, independent crash recovery, original
v309 behavioral parity, real v312 compatibility or proven original
freeze root cause exists.

A single-file lock also means a background autosave can temporarily
delay a confirmed EDT deletion. For fully nonblocking user edits,
future design must separate **UI mutation, durable commit and UI
acknowledgement**, with retry/rollback semantics and a bounded
queue; merely adding threads is not sufficient.

No production client, live v312 Java, user account/history, friend's
package or normal-host game session was executed or modified. No
independently verified isolated guest with blocked egress and
immutable production mounts has been established.

**Keep draft/unmerged. Never publish private original or modified
source, binaries, credentials, histories or dependency bundles.
No launch/release/distribution authorized.**
