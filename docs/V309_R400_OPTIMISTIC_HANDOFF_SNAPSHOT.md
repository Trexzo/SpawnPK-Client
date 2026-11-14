# R400 — optimistic panel/pending handoff snapshot

**Repo:** Trexzo/SpawnPK-Client. **Stack base:** R399 draft PR #1195.
**Status:** DRAFT/UNMERGED. The private source release and runtime launch gates remain CLOSED.

## Specific issue

R399 improved callback epoch checks and pending-drop identity draining, but
the ordinary \`persistHistory()\` method read two data sources separately:

1. A synchronized snapshot of the Swing Loot Tracker panel.
2. Later, a snapshot of the pending-drop queue under the history gate.

An EDT callback between those snapshots could transfer a drop from pending
to panel. Depending on the exact interleaving, the same drop could appear
in **both** snapshots (duplicate) or **neither** snapshot (lost).

Fixing this by holding \`r395HistoryGate\` while performing expensive
Swing rendering or invoking the EDT would expose another deadlock/freeze
risk, particularly around login and plugin restore. The panel getter
already has its own monitor.

## Private R400 candidate

The new experimental owner-local R400 copy changes only
\`rs/plugins/loottracker/LootTrackerPlugin.java\` from R399.

- Every session-valid live-drop Swing callback increments a handoff
  version to an **odd** value just before moving the record into the
  panel, and increments it back to **even** in a \`finally\` block after
  identity-based removal from the pending collection.
- \`persistHistory()\` takes a starting even version, obtains the
  panel records **without holding the history gate**, then under the
  history gate confirms the version is unchanged and even before taking
  the pending snapshot and mutation watermark.
- If the version changed or was odd, the save retries the snapshot.
  The retry limit is **five**; if none is consistent, it sets the
  existing \`savePending\` flag and returns without writing an
  ambiguous history.
- A failed or partially applied panel handoff marks the history
  \`unsafe\`; ordinary saves and early-shutdown merges refuse
  overwriting the original file. Explicit user history clearing
  resets that flag and invalidates the version.
- The R399 session-epoch protection, strict R396 read/receipt guards,
  identity-only pending acknowledgement, R398 unresolved-panel
  preservation, and R397 clean-stop no-op remain in place.

This closes the **specific handoff boundary** in the source design,
without introducing nested history/panel locks. It does **not** make
all panel modifications serializable: other UI actions, clears,
restore callbacks and cross-process storage writers require separate
audit. A normal history write still synchronously serializes to disk.

## Owner Windows evidence

- Copied the R399 private source tree into a fresh isolated
  \`R400-Private-Atomic-Handoff-Snapshot\` directory under the existing
  owner TEMP workspace; no prior candidate or golden source was edited.
- Owner JDK21 \`javac --release 11\` built **1,277 Java sources →
  1,388 class files**, exit 0.
- Exhaustive compiled byte comparison with R399: **exactly one
  changed class**, \`LootTrackerPlugin.class\`. Comparison to R381:
  only the existing two Loot Tracker classes differ.
- SHA-pinned read-only \`tools/r400/audit_optimistic_handoff.py\`
  audited the actual owner-private source/class trees:
  \`R400_PRIVATE_OPTIMISTIC_HANDOFF_STATIC_GATE_PASS\`, exit 0.
  It verifies the bounded version checks, unsafe-on-failure branch,
  no panel getter/render nested under the history gate, source/class
  change scope and fail-closed release flags.
- Public-only synthetic checks on owner Windows:
  **25/25 Python negative/positive controls** and
  **16/16 Java deterministic interleaving cases**, including a
  two-thread snapshot/handoff exercise, passed.
- Private compiled custody JAR:
  \`R400-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\`, SHA256
  \`bf1103d661ec4971a4fe2dbe6b07457ef3fef969f6419255d89c9b3b3abe4c17\`.
  The JAR was **not launched, loaded, shared or deployed**.

## Explicit limitations and follow-up

**These are static source/bytecode validations and invented synthetic
models, not a real recovered-plugin execution test.**

Not established: true EDT callback and client-thread interleavings
inside the original runtime, reentrant edits from other panel
producers, stale history-write completion after clear, filesystem
multi-writer serialization, complete durability on power loss,
original v309 behavioral parity, compatibility with the live v312
client, or the root cause of the original frozen client.

The storage journal from R397 is still a separate standalone research
prototype. This PR does not install any journal or modify existing
history files. Dirty shutdown may still block the Swing EDT on large
history files and the rate-limited retry may be delayed while shutdown
is in progress.

Do not launch the private game client on the owner's normal desktop.
No verified isolated guest with both denied external egress and no
writable production mounts has been established.

All private source release, game launch, merge and distribution flags
remain FALSE. Keep this PR **draft/unmerged**.
