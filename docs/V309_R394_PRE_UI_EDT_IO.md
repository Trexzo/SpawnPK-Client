# R394 — startup chains before first GUI: EDT history I/O and loadout cleanup

**Repository:** Trexzo/SpawnPK-Client. **Parent:** R393 draft PR #1189.
**Keep DRAFT, UNMERGED; Source-M1 private-source release gate CLOSED.**
Only public-safe source-free tooling, synthetic CI/tests and this report.

## Verified owner-private analysis — NO client execution

The authorized Windows PC retains a private R381 source ZIP inside an isolated
TEMP workspace (SHA-256:
902e3b583840073c095ea51c5fe5bee4034340ab92bd19dc7c36f3173f092f96).
The R394 Python verifier read and masked all **1,277 Java files in memory**
without extracting or executing anything; exit 0 and status
\`R394_STATIC_PRE_UI_EDT_IO_WITNESS\`. No owner cache/history/account file
was opened and no private recovered Java source or bytecode uploaded.

The scanner verifies method chains and narrow source-only facts:

1. Bootstrap calls \`loadPlugins\`, then \`startPlugins\`, then \`ClientUI.show\`.
   \`PluginManager.startPlugins\` dispatches \`startPlugin\` on Swing's
   event-dispatch thread (EDT) via \`invokeAndWait\`. The plugin's \`startUp\`
   runs on that thread.
2. \`LootTrackerPlugin.startUp\` constructs \`LootHistoryStore\`, calls
   \`deleteStale\` and then \`loadHistory\`. The last method schedules an
   \`invokeLater\` callback which calls \`historyStore.load()\`.
   \`LootHistoryStore.load\` performs file I/O and JSON parsing and permits
   history files up to **64 MiB** before refusing the read. This is a
   plausible EDT latency source, **not a measured startup delay**.
3. The main UI \`show()\` also posts an \`invokeLater\` callback **after**
   the plugin-start process. A separate synthetic, headless Swing/JDK21
   fixture confirms that a callback queued from \`invokeAndWait\` during
   synthetic "plugin startup" precedes a later synthetic "show" callback.
   The fixture executed no private client classes and did not open a GUI.
4. The loadouts plugin constructs \`LoadoutsPanel\` during its startup.
   The panel constructor initializes icon workers, loads folders, writes
   folder-order settings, and contains **six explicit File.delete() calls**.
   A default/legacy load path also includes a conditional deletion branch.
   Folder-order write delegates through a lock-taking method to a helper
   using staged file write and move. None of these operations were invoked
   by the audit.
5. Loadouts \`ImageLoader\` constructs a fixed pool of **five threads**,
   submitting \`LoadoutIconWorker\` tasks whose \`run()\` bodies are empty in
   this source revision. The global source scan found **zero explicit
   \`field3284.shutdown()\` / \`shutdownNow()\` call sites**. This warrants
   thread lifecycle inspection. It does *not* prove leaked OS resources,
   app shutdown hangs or actual worker activity; the program may terminate
   threads by another route, including process termination.

No production file was modified. No network socket or update service started.

## Verification

Public R394: one generic SHA-pinned, non-extracting 10-class source-chain
verifier; **25** source-free negative/positive tests, including a real
headless synthetic JDK Swing queue-order test; a 4-way Windows/Ubuntu
Python3.11/3.13 JDK21 workflow; and this report. The owner Windows local
synthetic suite returned **25/25 PASS**. The private auditor reported
\`launch_authorized=false\`, \`runtime_freeze_root_cause_proven=false\`,
\`client_executed=false\` and \`real_user_data_accessed=false\`.

## Scope and unresolved proof

Source matching is conservative: it establishes named calls and source
structure, not runtime reachability, precise performance, enabled plugins,
thread scheduling in the real client, or source/bytecode equivalence to the
original v309. The successful headless Swing fixture proves event ordering
only in a standalone toy example.

The next engineering target is to isolate potentially slow history loading
from the EDT **without changing the existing persistence, pending-record,
already-loaded and shutdown semantics**, and to audit icon-worker lifecycle.
Any changes to owner-private Java sources must stay private and receive
dedicated isolated regression coverage before integration. A true graphical
test requires a verified disposable Windows guest with disabled egress and
no writable production mounts. Do not launch the client on normal Windows.

Unproven: real game graphics/login/reconnect, actual startup-freeze root
cause, original-v309 behavioral parity, live-v312 compatibility, power-loss
durability or safe automatic staging cleanup. No PR merge or release approved.
