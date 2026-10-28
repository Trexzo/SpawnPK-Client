# R327 — durable inventory worker crash and reconnect fault injection

28 October 2026. Public, source-safe summary from the owner-private **v309 recovered-client** research lane. No proprietary game Java, production JAR, cache, accounts or backend code is published.

## Gap after R326

R326 verified that an undeployed reference dispatcher can reject stale inventory snapshots, serialize outgoing opcode53, and fence a broken transport. Its in-memory duplicate-action keys do **not** survive a game-server worker crash. R327 tests a durable idempotency layer for the server's **internal job queue**.

The existing v309 **outgoing seven-byte inventory drag opcode214 has no client-generated request ID or expected inventory revision**. Hence this reference cannot prove that two identical actions received from separate client logins are the same request. The queue must give an internal job a stable ID before workers retry it.

## Source-only R327 implementation and verified acceptance

[Private draft PR #4](https://github.com/Trexzo/fullspkclient-private/pull/4) now includes:

- `recovery/v309-r327/durable_inventory.py`: SQLite WAL/FULL-synchronous reference authority with an atomic transaction coupling the inventory revision, slot order, and account-scoped job outcome. Same job/payload replays return the persisted decision without another item swap. Reused job ID with different arguments fails closed; even stale and invalid outcomes are recorded.
- `recovery/v309-r327/recovery_bridge.py`: reconstruct the R326 current-generation single writer from durable state. An injected partial send taints the socket and forces a reconnect/full-widget authoritative resend. Durable revision gaps cannot silently produce fake in-memory revisions.
- `recovery/v309-r327/run_fault_matrix.py`: **75 deterministic offline failure scenarios**. The matrix injects 25 pre-commit rollbacks, 75 simulated post-commit/before-reply interruptions, 75 persisted duplicate suppressions, 75 damaged transport fences and 75 independent reconnect/reassertions. The simulated partially transmitted opcode53 payload spans every **0–9 byte prefix** of the ten-byte full-inventory update.
- `test_durable.py` and `test_fault_matrix.py`: **25 source-only tests**, including a genuinely separate Python child process exiting with code73 immediately after committing SQLite state; a later reader verifies the transaction survived and the same server job is never committed twice.

A clean extraction of the sanitized **R327 source/test-only ZIP** passed its SHA-256 manifest, **25/25 unit tests**, and the repeated **75/75-scenario matrix**. Deterministic scenario manifest SHA-256 `863ef50af9e358ddc593a807fcba10ae9a75dba0715fa11986689f89cff06a5e`. The final database-model inventory is revision21: Logs ID1511 x1 in slot0, Coins ID995 x7 in slot1. The new connection emits the source-format incoming widget3214 opcode53 with that state. Neither the client nor a real network is involved in the R327 matrix.

## Original-client continuity and explicit limitations

Before R327, the original R326 private GUI evidence ZIP SHA-256 `c5bbc7d4900256e533a06c7fcef73b1ba256a6696d11188abb93aa01a8157928` was reverified against its preserved screenshots, socket receipts and **25/25 R326 tests**. Its two authentic original-client GUI sessions remain the **most recent GUI acceptance**. **R327 has not conducted a new original-client GUI run**: its new evidence is offline SQLite/transport fault injection, not live-server crash recovery.

No production game backend or original v309 client has been modified. No claim about actual SpawnPK database transactions, power-loss durability, stable client action IDs, Windows-native GPU, authenticated game service, multihour operations or original-v311 bytecode parity is made.

The separate **1,277 recovered Java source files and three private JARs are not yet bulk-imported to the owner-private GitHub branch**. Keep [private issue #3](https://github.com/Trexzo/fullspkclient-private/issues/3) OPEN until an actual complete, hashed Git tree is present. Both [public PR #1143](https://github.com/Trexzo/SpawnPK-Client/pull/1143) and private PR #4 remain draft and unmerged, preserving unrelated owner-main work.
