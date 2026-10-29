# R328 — original v309 client after interrupted inventory response

29 October 2026 · Source-safe public summary. The original recovered game Java and private assets are not uploaded here.

## Authentic graphical acceptance

Two independently launched Java client processes ran the **unchanged** source-built 1,386-class v309 game JAR SHA-256 `b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721`, original 10,772-file owner cache, Linux/Xvfb 1400×900 and a synthetic game server bound **only to 127.0.0.1**. Both original GUI sessions loaded region13386. No live game account or production backend used.

**Phase A — clean test exit0 at 23.42 seconds:** the localhost server opened tab3 parent3213 using incoming opcode71 and populated inventory widget3214 using correctly framed incoming opcode53 (Coins item995 x7 slot0, Logs item1511 x1 slot1). An actual AWT mouse drag from inventory slot0 to slot1 made the real client send ISAAC-decoded **outgoing opcode214**, payload length **7**, widget3214/slot0→slot1/move-mode0. Raw actual-client captured wire SHA-256 `4ea2d36cf683a87df01a9dde293ffa588609dcd668bc46343bd25c00b8b73a0a`, length67 bytes. Test server atomically committed the user interface action to a local R327 SQLite durable journal (revision20→21, exactly one internal server job; Logs slot0, Coins slot1).

Then the test server **deliberately sent only five bytes of an eleven-byte incoming inventory opcode53 frame** and closed its TCP socket. The exact captured partial frame `4f0c8e0002` was SHA-256 `efa788df5e994cc5f12f1b501594f525f3a7399c00947cc84ce2d6e61b9229e5`. The original v309 client was not modified to make the incomplete frame valid.

**Phase B — clean test exit0 at 19.51 seconds:** an independent new Java client and new synthetic server read the same persisted SQLite revision21. The new session received **two complete incoming opcode53 snapshots** (restored state and authoritative resend). Original-client inventory screenshot differed from the old pre-swap state by **1,131 item-region pixels** and stayed unchanged after resend (**zero changed pixels**). SQLite `PRAGMA integrity_check` returned **ok**, and exactly one committed internal action was present.

The first exploratory fixture tests were **not accepted**: one had incorrectly framed opcode53 data in the mock server, and a separate orchestration retry did not complete second login. The final accepted runs above used corrected test-only framing and persisted original server receipts.

## Reproducibility and limits

[PRIVATE draft PR #4](https://github.com/Trexzo/fullspkclient-private/pull/4) contains `recovery/v309-r328/verify_replay.py`, ten independent synthetic positive/negative receipt tests, and this acceptance's SHA-pinned report. The **exact owner-private mock server, GUI runner, decoder patch, AWT robot, screenshots, original wire, five-byte server fragment and SQLite database** are included in the supplemental owner-private `SpawnPK-v309-R328-Private-Interrupted-Inventory-Reconnect-Acceptance.zip` (28 files, 675,506 bytes), SHA-256 **`79e3aea38f2177bb799da9b750ac4597c1c3a7618e2ccfc7ab18e5fb518d38f8`**. The archive passed clean-extraction SHA manifest, independent GUI receipt verification and **10/10** synthetic tests. No original compiled game JAR or 203MB cache is in the supplemental ZIP.

**Do not overclaim:** R328 demonstrates recovery in a **fresh Java client process** after a truncated synthetic-server reply. It does **not** prove automatic in-process reconnect by the damaged client, live SpawnPK server inventory/database behavior, physically durable power-loss recovery, native Windows GPU, or original-v311 exact-bytecode parity. No production Java code or original compiled JAR changed.

The original full **1,277 recovered Java source files plus three pinned private JARs still have NOT been bulk imported into the private GitHub branch**, tracked at [private issue #3](https://github.com/Trexzo/fullspkclient-private/issues/3). Preserve separate owner development main; keep public PR #1143 and private PR #4 DRAFT/UNMERGED.
