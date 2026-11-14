# R397 — clean-shutdown fast path + standalone crash-recovery journal design

**Repository:** Trexzo/SpawnPK-Client. **Stack base:** R396 draft PR #1192.
**Owner-private reconstructed source / binary release gate CLOSED. Keep DRAFT / UNMERGED.**

## Actual private source change

The R396 pre-restoration shutdown fallback strictly parses and rewrites
the complete loot-history file even when no new loot has arrived since
the plugin began starting. That can block the Swing EDT unnecessarily
and needlessly replace a fully valid on-disk file.

R397's private candidate adds a narrow no-op branch near the start of
\`r396FinishStopMerge()\`, after the existing rememberLoot/store/panel
guards and **before the first strict disk read**. The branch returns
success only if all three are empty:

1. Pre-restoration live-drop buffer (holds exact drop occurrences).
2. Ordinary pending-drop queue (includes callbacks not yet applied).
3. Existing panel history, snapshot through the synchronized off-EDT getter.

When any collection is populated, the R396 strict read + merge + verified
staged-write behavior remains unchanged. The optimization does not
interfere with the already-loaded normal save path. It cannot address
concurrent event admission after plugin shutdown begins; this has not
been tested in the actual game.

## Actual Windows verification

- Created disposable owner-private \`R397-Private-Noop-Shutdown\` as a copy
  of R396, under the existing isolated temporary workspace. The R381
  golden ZIP, R395 and R396 owner-private sources and the live v312 folder
  were not modified.
- JDK21 \`javac --release 11\` compiled **1,277 Java sources → 1,388
  class files**, exit 0. Compared all class files with the R396 build:
  **exactly one changed class**,
  \`rs/plugins/loottracker/LootTrackerPlugin.class\`. Compared with R381,
  only the same two loot classes from R396 differ.
- A SHA-pinned R397 verifier (using inherited R396/R395/R394/R393
  read-only parsers) independently checked the real owner-private
  source-and-class trees. It verified the three-part guard structure,
  its position before the strict disk read, retention of the dirty
  merge path, and exact source/class delta. Status:
  \`R397_PRIVATE_CLEAN_STOP_STATIC_GATE_PASS\`, exit 0.
- A private output JAR was packaged **but not executed or installed**:
  \`R397-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\`, SHA-256
  \`d95395582b9a8d5661963d352572ee6562aafc88cbfbdf0acf3641f2d1e4b56f\`.
  The file exists only in the owner's isolated TEMP workspace.
- **15/15** public synthetic Python negative/positive tests passed
  locally, including omission of each of the three guards, guard
  after I/O, fake guard in comment, fail-open output, SHA drift and
  unexpected additional class/source changes.

## Crash recovery: prototype only, no game integration

A separate **synthetic, public, standalone JDK11-compatible Java model**
explores a crash-recovery protocol. It never references recovered game
source, launches the game or reads user histories.

The protocol experiments with SHA-free CRC-framed append-only event
journal entries, monotonic event IDs, per-append FileChannel.force(true),
an atomically moved snapshot containing the last applied event ID
(a replay watermark), and strict rejection of truncated/corrupt frames
or conflicts between committed events and journal entries. Replaying
a journal after a successful snapshot commit must not count the same
event twice. Equal-looking drops with separate IDs remain separate.

**12/12** local owner Windows/JDK21 scenarios passed: simulated abrupt
stop before snapshot commit; replay after committing but before journal
cleanup; repeated identical drops; appending after a watermark; clean
snapshot no-rewrite; injected save failure; truncated journal; corrupted
CRC; corrupted snapshot; inconsistent committed frame ID/payload;
oversized record; and symlink refusal.

**This is a design and toy executable, NOT a completed solution for
SpawnPK.** The real loot history format does not currently contain the
synthetic watermark and durable event ID fields. Supporting this
requires careful versioned format migration and replay/commit semantics.
No new journal was added to \`LootTrackerPlugin\` or
\`LootHistoryStore\` during R397.

Other prototype limitations: one-writer assumption, no journal
compaction/rotation, bounded journal size that can fill up, no
independently verified parent-directory fsync, no power-loss storage
guarantee, no atomic multi-file transaction, no OS crash testing, and
no verified live application event admission ordering. A partial
tail is reported as corruption rather than silently discarded, so
manual recovery remains necessary in some cases.

## Release and performance gates

The source-only guard is not a measured performance result. The dirty
shutdown fallback can still parse up to 64 MiB and rewrite history
synchronously on Swing's EDT. The journal prototype cannot be deployed
as a storage replacement without runtime tests and a migration plan.

Actual private plugin runtime/GUI/login/reconnect, external egress
blocking, startup freeze root cause, power-loss durability, concurrent
writers, failed disk writes, original v309 parity and compatibility
with live v312 all remain unverified.

No private source, compiled JAR, credentials, cache, user data or
production client artifacts were committed to the public repository.
No private game client was launched. No source release, merge,
installation, update distribution or production cleanup authorized.
