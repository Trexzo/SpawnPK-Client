# SpawnPK v309 R284 — authentic legacy-OSRS GUI Cook action, socket receipt and synthetic response

**2026-10-19 — sole SpawnPK-Client integration chat.** Existing PR #1142 remains **DRAFT**. **No production source changes, no main merge.** Uses the *actual* previously full-source-built R278 Java11-target 1,386-class JAR (SHA256 \`dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd\`).

## First real OSRS-region graphical Cook proof

The isolated localhost GUI was reconstructed from five SHA256-verified original owner archives and 10,772 cached game files. A synthetic source-framed **opcode73 region packet targeting center (420,596)** was issued after dummy local login. **Important correction of R283's proposed target:** the actual game's region selection did **not** select proposed region13129. Its original real GUI logs show:

\`\`\`
[Region] Stand in region: 13386
[Region] Region group: white_portal
[Regions] Loaded region ID: 13386 (field1134)
\`\`\`

Region **13386** is also part of the original \`Client.field407\` legacy-OSRS list, and the actual runtime selected **\`ObjectDefinition\` bank \`field1134\`**. The 504×335 world rendered >99.7% nonblack under Linux/Xvfb using original client non-class UI resources. Real AWT right-click on the original cache model ID114 at screen (514,318) visibly opened an **actual "Cook Cooking range"** option; AWT first-option left click (483,349) caused genuine outbound **6-byte opcode132**.

A **separate localhost TCP listener (127.0.0.1:43594)** independently framed/ISAAC-decoded that *client-originated* object packet. It validated **ID114**, world **(3362,4769)**, raw byte offset **44**, and separately sent inbound **opcode253** synthetic chat \`Object 114: isolated test interaction.\`. The client original opt-in \`PacketCapture\` independently confirms outbound **121** map-ready, inbound original nested opcode60/22 mixed object updates, outbound **132/6**, and inbound **253/39**. **This is real menu selection + socket receipt; it does not implement actual cooking/inventory or a real SpawnPK server.**

## Independent successful GUI sessions

| | First real GUI capture | Second isolated GUI capture |
|---|---:|---:|
| Active bank, actual selected region | \`field1134\`, 13386 | \`field1134\`, 13386 |
| Server-decrypted action | opcode132/6, ID114 | opcode132/6, ID114 |
| Raw wire offset | 44 | 44 |
| World target | (3362,4769) | (3362,4769) |
| Original ciphertext bytes at receipt | 51 | 51 |
| Ciphertext SHA256 | \`92c847db63befcea7fbae45359276b3bdbda636f0b35df1cbc53a094578dc1da\` | \`5bcf54824e1b053c161c5365ac2a788a76a0452c4d7b7ada6fc1be2a64323aaf\` |
| Test-only server chat response | opcode253 | opcode253 |

The second successful capture used a separately, checksum-verified staged owner-archive home, and its Cook Robot returned exit code 0. An earlier clean-home attempt failed the Robot helper before a Cook receipt; it is **excluded** from success totals. A subsequently attempted integrated **one-command wrapper stalled**, despite confirming rendered world/field1134/map-ready. **Do not claim that wrapper has passed end-to-end.** The included runner is experimental; its source-backed stage and direct GUI components are independently documented.

Previously verified R283 original compiled-client region/bank regression **35/35 PASS**, unchanged. The real GUI acceptance adds the interaction beyond that offline test, not another full client build.

## Reproducible, owner-safe evidence

\`SpawnPK_v309_R284_REAL_OSRS_GUI_COOK_LOOPBACK_EVIDENCE.zip\`, SHA256 **\`faec8c977f6127b44ae44c53c72e6e5a1c4e78757c7c4e221850c986343bbff5\`**, **1,185,148 bytes**, **35 ZIP entries**. Two independent deterministic builds were byte-identical; ZIP CRC and per-file SHA256 passed. The separately authored standard-library + Pillow evidence verifier reported **162/162 assertions PASS**, inspecting both real raw socket ciphertext files, original client packet captures, actual region logs, screenshots, response pairing and SHA hashes.

Contains public-safe independently authored synthetic localhost server and ISAAC/packet framing helpers, AWT Robot/login scripts, exact-archive-safe cache-staging helper, experimental one-command fresh GUI runner, prior R283 pass log, two real screenshot/ciphertext capture sets, and evidence validator. Does **not** contain any original/reconstructed game source, compiled game classes, dependency JARs, original asset/cache files, font binaries, or user credentials. No original login/network access.

## Strict remaining acceptance gates

- The actual client GUI selected **Cook**, but the mock server only returned a **synthetic chat**, not cooking animation, food handling, real inventory effects, or original game-server behavior.
- The full automated one-command GUI wrapper is **not reliability-accepted**; the successful direct GUI runs and source-backed stager are distinguished.
- This R284 run did **not** perform another complete 1,277-source rebuild. It uses the previously checksum-pinned full R278 compiled client.
- Native Windows GUI, live server authentication, real interactions/quests/combat, long-running game sessions, cache compatibility across all maps, and original client bytecode parity remain unverified.

**Next R285:** stabilize the fresh-home GUI runner with explicit child-process, Robot and screenshot lifecycle diagnostics; then undertake meaningful native-Windows graphical acceptance. Preserve PR #1142 DRAFT, no automatic merge or installation.
