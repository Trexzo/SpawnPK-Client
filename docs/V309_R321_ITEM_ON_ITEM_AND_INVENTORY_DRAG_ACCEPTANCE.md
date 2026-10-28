# R321 — actual source-built v309 inventory Use-with and drag/drop acceptance

28 October 2026. **Real owner-private recovered client**, original 10,772-file authentic game cache, isolated Linux/Xvfb desktop and synthetic **127.0.0.1:43594** game server. The running executable was **only** the unchanged full-source-compiled 1,386-class production game JAR, SHA-256 `b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721`, no Java diagnostic overlay, collision override or production-source change.

## Original-client GUI item on item

The local server used opcode71 to open interface3213 on tab3 and incoming opcode53 to display seven Coins (item995) in inventory slot0 and one Logs (item1511) in slot1, widget3214. A real Java Robot clicked `Use Coins` then right-clicked the Logs; genuine in-game menu **`Use Coins with Logs`** was visible and selected. Original source Client.menuAction870 generated **actual outbound ISAAC opcode53**, length **12 bytes**. Local test server independently decoded all fields: **source item995 / slot0 / widget3214, target item1511 / slot1 / widget3214**, and replied with synthetic opcode253. The original client rendered that response. This is client/protocol acceptance, not a production valid recipe.

## Original-client GUI drag-and-drop

A separate actual GUI mouse-held drag from slot0 onto slot1 caused genuine source-built Client to emit **outbound opcode214**, 7-byte payload **widget3214, slot0→slot1, move-mode0**. The local server independently decoded this packet and **then** sent server-authoritative incoming opcode53 reordering the inventory. Original game framebuffer screenshots before and after drag changed **1,132 pixels** in the item rectangle, with Logs and Coins visually swapped.

## Acceptance and provenance

A preliminary standalone item-on-item 27.31-second GUI replay exited 0. A combined item+drag replay exited 0 in 30.30 seconds; a final checksum-strict replay (adding the original drag packet's wire offset) exited **0 in 30.00 seconds**. No client source/JAR changes at any stage.

| Independently observed wire | Bytes | SHA-256 |
|---|---:|---|
| Outbound opcode53 item-on-item witness | 58 | `3f238eeaa2c8052d5c471ab889b1ae06aa740fc4dee5b2c5b1eedfe62cac178d` |
| Cumulative outbound opcode214 drag witness | 69 | `40c6ab419c1ebbf54d6c4da3f9412ad0987cc3cb90abbb62840d6f47f87b5e1f` |

Owner-only original asset screenshots are stored outside the public repository; genuine `Use Coins with Logs` context screenshot SHA-256 `613775a76e031fe4a72d22b54d8f18e7ab1889c206c082f149641d1f052ace14`, final after-drag screenshot SHA-256 `1bd78348bca522933db35e55265fb408e9c7885f4303e7ad0feae8981d0de27a`.

**All source-safe development now on [private PR #4](https://github.com/Trexzo/fullspkclient-private/pull/4)** under `recovery/v309-r321/`: SHA-pinned owner-private R315 source test fixture builder, exact source-verified opcode53+214 codecs, two actual Java AWT UI robots, real GUI acceptance runner, genuine packet/screenshot receipt verifier and synthetic negative+positive tests. CI runs those original-independent code checks on Windows and Linux. This public document contains no owner private game Java, client binaries, cache or accounts.

**Explicit limitations:** localhost synthetic-server only, Coins+Logs is not a confirmed live-game recipe, drag persistence across relog not verified, live authenticated server not tested, owner-native Windows GPU not tested, exact original-v311 bytecode recovery is separate. **All 1,277 recovered private Java sources and three pinned JAR files still require their separate GitHub import**, tracked at [private issue #3](https://github.com/Trexzo/fullspkclient-private/issues/3). Keep both PRs DRAFT and UNMERGED.
