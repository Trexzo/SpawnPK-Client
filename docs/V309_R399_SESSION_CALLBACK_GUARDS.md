# R399 — session-scoped Swing loot callbacks and identity-based commit acknowledgement

**Repository:** Trexzo/SpawnPK-Client. **Stack base:** R398 draft PR #1194.
**DRAFT / UNMERGED. Owner-private source release gate CLOSED.**

## Exact source-backed problem

The R398 private Loot Tracker queued individual live-drop Swing callbacks with
\`SwingUtilities.invokeLater\` without recording the issuing plugin session.
The history restoration callback already checked its generation, but the
live-drop callback did not. A drop callback queued before plugin disable could
therefore run after re-enable and append the older drop to a newer panel,
remove a pending item or trigger a save.

The R396 shutdown merge and ordinary save also left an edge case: a pending
drop already included in an acknowledged file commit could remain in the
in-flight list because its old Swing callback never ran. A subsequent
save could append it again. Treating two records as equal by mob/source title
or type would be wrong; distinct identical-looking drops must survive.

R398's unresolved-panel check also needed to consider in-flight pending and
pre-restoration records even when the visible panel was empty.

## Owner-private experimental R399 candidate

R399 copies the isolated R398 private sources into an independent owner-TEMP
workspace and edits **only**
\`rs/plugins/loottracker/LootTrackerPlugin.java\`.

- A plugin-session epoch increases at startup and again at shutdown.
  Startup opens a private admission flag; shutdown closes it before
  the dirty-history merge. Live-drop admission checks the flag and
  records the issuing epoch under the existing restoration monitor.
- Each queued Swing drop callback checks that the issuing epoch still
  belongs to the active plugin before touching the panel, removing
  pending entries or requesting a save. A stale callback returns without
  mutating the new panel.
- A verified early-shutdown merge snapshots the exact pre-restoration
  record objects that were written. Only after a successful file-save
  receipt are those same object identities removed from pending.
  Title/type equality is never used to remove a committed instance.
- The normal save path snapshots pending records under the existing
  monitor, writes the panel snapshot plus those pending records, and
  removes *only those snapshotted identities* after an acknowledged save.
  A monotonic admission/mutation counter prevents a save from being
  declared fully up to date when a new drop entered after its pending
  snapshot.
- New startup treats retained pending or pre-restoration drops as
  unresolved even if its panel happens to be empty, closing a known
  R398 fail-open route. It refuses automatic restoration/overwrite
  in that situation rather than inventing deduplication identities.

The private original golden R381 source archive and R398 source candidate
remain unchanged. **No live v312 binaries, user data, launchers, updater,
friends' files or production persistence were opened or modified.**

## Verified Windows private build and static evidence

- Owner Windows JDK21, \`javac --release 11\`: **1,277 Java sources
  compiled to 1,388 class files**, exit 0.
- Full bytewise comparison of the entire compiled class set versus R398:
  **exactly one changed class**,
  \`rs/plugins/loottracker/LootTrackerPlugin.class\`. Compared to R381,
  only the same two Loot Tracker classes established in R396 differ.
- SHA-pinned, read-only R399 static gate against actual owner-private
  source and class trees: \`R399_PRIVATE_SESSION_CALLBACK_STATIC_GATE_PASS\`
  exit 0, with release/launch/merge flags FALSE. The gate uses the
  inherited R396 source-contract checker on an **in-memory normalized
  view** of two R399-changed tokens and separately verifies their
  new stricter R399 semantics. It neither changes nor releases the source.
- **23/23 Python synthetic negative/positive checks PASS** on owner
  Windows Python3.12; **16/16 Java standalone synthetic restart,
  callback, identity and admission tests PASS** on JDK21.
  One test uses two real synthetic Java threads with synchronized
  admission after a stop. The models do not execute private game classes.
- Owner-local, **DO NOT RUN OR SHARE** private candidate archive:
  \`R399-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\`, SHA-256
  \`f03f674d368a5eb15fa9a0e4fe89fa0158c3ed7a28ae02f7d05edc2e1ba7caf5\`.
  It was packaged for offline custody only and not loaded/executed.

## Still not proven; explicit next controls

The source-level changes and separate synthetic model are not real
plugin-runtime tests. The R399 normal-save snapshot still obtains panel
rows and pending entries separately; an EDT callback handoff between
those snapshots could cause an omission or duplicate in ways that
the simple synthetic model does not exhaustively exercise.

The candidate also does not generationally guard *every* Swing callback
for pricing, filtering, UI rebuild and image refresh. The R399 focus is
live-drop callbacks and pending identities only. Existing reentrancy and
event-source ordering during actual plugin disable/re-enable still need
isolated runtime inspection.

No persistent per-drop IDs or crash-recovery journal were integrated.
Do not claim zero data loss on disk-full, OS crash, power loss, concurrent
writer or corrupt history. The R396 dirty-shutdown fallback still can
block the EDT on large files. Original v309 behavioral parity, live v312
compatibility and the real freeze root cause remain unproven.

No disposable guest with independently verified egress denial and no
writable host production mount has been established. **Do not launch the
private game client on the owner's normal PC. Do not merge, deploy,
distribute or release the private reconstructed candidate.**
