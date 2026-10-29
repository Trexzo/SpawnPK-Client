# R325 — adversarial multi-revision inventory, already-sent stale packet and fresh reconnect

28 October 2026 · Public **source-safe** summary from owner-private reconstructed **v309** client GUI acceptance. Original recovered game Java/JAR and full asset cache are not uploaded to this repository.

## Real unchanged-client graphical tests

Owner-original 10,772-file cache, unchanged **1,386-class source-built v309 production JAR** SHA-256 `b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721`, isolated Linux/Xvfb 1400×900 GUI, synthetic ISAAC server bound to **127.0.0.1**. No live SpawnPK account, production server or Java diagnostic overlay.

**Phase A — 22.5 seconds, exit 0:** client originally displayed saved server inventory epoch1 (Logs in slot0, Coins in slot1). Local server atomically committed epoch2 (Coins slot0, Logs slot1), invalidated a queued unsent epoch1 snapshot and refused a delayed epoch1 write. The actual original-client inventory changed **1,131 pixels** after opcode53 authoritative epoch2. Next the fixture deliberately **bypassed the send gate and transmitted an old epoch1 opcode53 already past the socket boundary**. This really reverted the game's visible inventory by **1,131 pixels**. A subsequent server-authoritative corrective opcode53 epoch2 restored the correct view with **0 changed pixels** relative to the previous correct epoch2 screenshot. The server wrote epoch2 to a local durable JSON file SHA-256 `be4af91c2c354d92e41353cfff15d9846e2f2de6e93358a4e6e16d4946cd8334`. Exact mock-server send ledger: **four real inbound inventory opcode53 frames** (initial epoch1, committed epoch2, deliberately stale epoch1, corrective epoch2), all 10-byte payloads.

**Phase B — 20.0 seconds, exit 0:** **separately launched original Java client** and synthetic server restored the durable epoch2 order. A stale epoch1 replay/snapshot and stale-write proposal were both rejected, and the server delivered **only two current epoch2 inventory opcode53 frames**. Original GUI item rectangle matched Phase A's accepted epoch2 result (0 changed pixels) and was unaffected by the redundant current-revision update (0 pixels). All test children cleaned.

**Independent fresh rebuild** of the exact fixture, from SHA-pinned R324 server/GUI preimages, reproduced all four output scripts byte-for-byte and passed **both real GUI sessions again**, 23.1 and 20.5 seconds. Visual deltas for the second run: commit 1,132; stale wire 1,132; authoritative correction 0; restored fresh login 0; current-revision resend 0.

**Engineering interpretation:** original inventory opcode53 carries no revision. A server-side ordered outbox prevents unsent outdated snapshots, but once an obsolete full-widget packet is transmitted the unchanged client can still display it. A current authoritative resend restores the display. Production-service ordering/database implementation has **not** been audited or modified.

## GitHub code and limits

Private [draft PR #4](https://github.com/Trexzo/fullspkclient-private/pull/4) now contains exact compressed test-only fixture patches, SHA-gated staging generator, genuine two-client screenshot/server-ledger verifier, and source-only adversarial tests (`recovery/v309-r325/`). Original client game binaries/cache and account data are not committed to the public repository. Hosted Linux/Windows CI is **source-only**, not itself an authentic game run.

Owner-private sanitized `SpawnPK-v309-R325-Private-Multirevision-Reconnect-Acceptance.zip` has **25 files**, **1,339,877 bytes**, SHA-256 **`2a22555f18da2e8f943ab1af63186c279cc947d3c5e73b1ebf017115dbe0a9a3`**. A clean extract verified every manifest hash and passed its independent two-session receipt verifier.

**No certifications** for real authenticated SpawnPK server, production database concurrency, native Windows GPU, multihour gameplay or original-v311 bytecode parity. **Original recovered 1,277 Java source files and three approved private JARs remain NOT bulk-imported into the private GitHub recovery branch**, tracked at [private issue #3](https://github.com/Trexzo/fullspkclient-private/issues/3). Preserve separate owner-development main, original-v311 parity research and both draft unmerged PRs.
