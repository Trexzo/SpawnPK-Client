# v309 R285 — reliable fresh-input legacy-OSRS Cook GUI replay

**2026-10-19. Sole active client integration chat, PR #1142 DRAFT.** R285 makes **zero production client-source changes** and reuses the earlier **complete Java11-target 1,277-source/1,386-class R278 rebuild**, SHA256 of private class-only JAR \`dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd\`. No main merge, no installed-client changes.

## What R284 left open

R284 had two real graphical OSRS Cook GUI/SOCKETS passes using the source-built client, but its complete, single-command fresh-archive wrapper stalled on a later run. That meant **interactive Cook was proven**, but its automatic owner-private-input-to-finished-GUI workflow was **not reliable**. A misleading early "rendered pixels" condition could occur before a queued object's model entered the scene; Java Robot/screenshot writes were also raced by the wrapper.

## R285 implemented test tooling and two independent **all-the-way fresh** successful runs

R285's **actual executed source-free** harness:

1. Verifies SHA256 for **all five original owner input files before any staging writes**: R278 private archive \`e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280\`; R265 owner snapshot \`9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb\`; original \`.spawnpk (4).zip\` \`8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565\`; original \`client(...).jar\` \`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38\`; R230 resource mapping \`5c21e5c643de759da80c4d18ebb6a49c84968d47a979caa33f7d4ad2170a7125\`.
2. Refuses to touch **any existing output directory**. Stages **10,772 authentic original cache files** in a new disposable home, constructs a private resources-only JAR locally, checks actual R278 class-JAR SHA, and compiles Java AWT helpers with \`javac --release 11\`.
3. Runs isolated **Linux/Xvfb 1400×900**, local-only TCP server \`127.0.0.1:43594\`, original rs.gui.Launcher and dummy local login. Await stages: real compiled GUI media loaded; Java RobotLogin completes exit 0; real client log shows \`[Regions] Loaded region ID: 13386 (field1134)\`; **actual map-ready opcode121 and nested object-spawn packet60** observed at independent listener; bounded **five-second object-model readiness** settling period; then real AWT **Cook Cooking range** menu and option clicks.
4. Captures real screenshots via temp-PNG **atomic rename**, verifies 1400×900 size and populated 504×335 viewport, reads actual decoded localhost socket receipt, verifies opcode**132**/6 for Cooking range **ID114** at world **(3362,4769)** and reply opcode**253** synthetic chat, independently SHA256-checks actual received bytes. Captures structured timeline and each child exit; gracefully terminates the isolated client/server process groups.
5. Bounds individual waits, Java Robot processes and the entire external Xvfb wrapper. Failure-path tests show **existing destination refusal** and **incorrect R278 hash refusal before creating output**. Neither required or touched installed Windows client.

**Two separate fresh owner-archive GUI runs completed exit code 0** (not reused staged homes), client/server GUI tests took ~25.8 and ~26.2 seconds after graphical subprocess start; original asset staging was performed independently each time. The TCP listener independently ISAAC-decoded one genuine action each run and returned one synthetic reply:

| | Fresh replay 1 | Fresh replay 2 |
| --- | --- | --- |
| Original asset cache files staged | 10,772 | 10,772 |
| Actual selected region/bank | 13386 / field1134 | 13386 / field1134 |
| Client action, object | 132/6, ID114 | 132/6, ID114 |
| World target | (3362,4769) | (3362,4769) |
| Raw wire offset | **45** | **45** |
| Received ciphertext bytes | **52** | **52** |
| Wire SHA256 | \`e6f8e16d2d66ca9ffb24a9253036e7e9a7d5e41c80dc2540e7d2a09d66d2fa24\` | \`1b8ea87b016d096cb2af7f1866377777f9bf6f9051cf3a5e95a6d4e7afad8194\` |
| Server synthetic response | 253, paired to 132 | 253, paired to 132 |
| Wrapped fresh run exit | **0** | **0** |
| Bounded child cleanup | Confirmed | Confirmed |

**Do not confuse R284 with R285:** R284 original ephemeral action offset44/51 received bytes; R285 controlled harness receives offset45/52 bytes due to session packet timing, not a source protocol change. Both real decoded streams are consistent with the same semantic action. Rendered screenshots of real Cook menu independently captured on both runs.

## Release evidence / portability

One **deterministic, source-free ZIP** \`SpawnPK_v309_R285_FRESH_GUI_OSRS_COOK_REPLAY_EVIDENCE.zip\`, **SHA256 \`99665e0404c2273b24b47935a8db6b5f169a2a1d17fff7d09fda928aaf021d33\`**, **1,641,367 bytes**, **42 entries**. Two independent deterministic builds were byte-identical. All ZIP CRC, per-entry size and SHA checks PASS; independently authored Pillow + stdlib verifier **228/228 assertions PASS**, including both independent fresh-home completion logs, literal raw byte hashes, actual decoded packet and response, original region logs, event ordering, child cleanup, eight real screenshots and the two negative test paths. The original owner game classes/JAR, original cache/index/data files, private non-class resource JAR and original font files **are not in the evidence package**.

One documented isolated replay command, starting from the original owner archives:

\`\`\`bash
python3 scripts/Run-R285-Fresh-GUI.py \
 --r278 '/private/SpawnPK_v309_R278_FULL_SOURCE_OBJECT_AUTHORITY_GUARDS.zip' \
 --r265 '/private/SpawnPK_v309_R265_UNIFIED_CACHE_R246_PLAYER_APPEARANCE_DIAGNOSTIC_PRIVATE.zip' \
 --assets '/private/.spawnpk (4).zip' \
 --original '/private/client(20261015-104312).jar' \
 --r230 '/private/SpawnPK_v309_R230_AUTHENTIC_ASSETS_LOGIN_PRIVATE.zip' \
 --output '/new/nonexisting/r285-clean-home'
\`\`\`

The source-free ZIP contains the **tested** complete Python fresh-stage/replay wrapper, bounded Python GUI process supervisor, atomic-screenshot AWT Java Robot, original-independent synthetic localhost server/ISAAC helpers, SHA-pinned asset stager, two actual independent GUI replay evidence sets, standalone archive verifier and exact-input/negative logs.

**Strict boundaries:** Native Windows GUI and existing owner's Windows-specific launcher are **NOT** tested; original game login/authentication and original cooking/inventory logic are **NOT** implemented; synthetic reply253 is **not proof of cooking gameplay**. The 26s scripted sessions are **not long-term live-world stability**. R285 did **not** rebuild the 1,277-source production client; it tests the *previously* fully compiled and SHA-pinned R278 JAR. Keep #1142 DRAFT, no merge to main.

**Next R286:** bring this guarded, reproducible runtime handoff into a native Windows launch acceptance at a meaningful integrated milestone and test Windows-specific AWT/graphics/packaging; in parallel begin actual server-side cooking/inventory behaviors only when backed by original client protocol/legitimate behavior evidence.
