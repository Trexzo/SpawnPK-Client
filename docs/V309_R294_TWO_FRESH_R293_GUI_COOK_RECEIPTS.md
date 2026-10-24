# SpawnPK v309 R294 — two independent real R293 Linux graphical Cook replays

**Completed 2026-10-19. This is actual source-built R293 Linux/Xvfb GUI acceptance, not native Windows.** No new production class/source changes; the R293 bounds guard and R290 object ID/scene hash authority are unchanged. Same DRAFT PR #1142; original private game binaries, cache, screenshots and logs stay outside public GitHub.

## Why R294

R293 fixed the real `ArrayIndexOutOfBoundsException` when stale menu actions passed off-scene X/Y or plane coordinates into `Client.handleObjectClick`, then passed a real 71-check JVM regression and rebuilt one changed `rs/Client.class`. But R293 did **not** yet have fresh GUI evidence. Previously passed R290 graphical sessions could not be cited as proof for a changed R293 binary.

R294 directly exercised the exact **R293 class-only JAR** SHA256 `0d0eedae92efe709b2d6eb49b1fc4432db174a6e68a7f06fd4fc2736d0f6cee9`, from private R293 release SHA256 `c6ecd187ced1f6bae2858b846b5940a58d71a08f7031e938f4a2a15bb214f2cf`. The original five owner archives, cache (10,772 original files, ~209.7MB), and authentic original client resources all passed pinned SHA checks. The original R285 **source-only bounded graphical replay** was retargeted through only exact anchored, source-verified edits; original R285 ZIP SHA256 `99665e0404c2273b24b47935a8db6b5f169a2a1d17fff7d09fda928aaf021d33` and three source member hashes are checked independently.

## Two genuine fresh sessions — both PASS

Each session extracted a fresh 10,772-file authentic test home, compiled Java 11 AWT login/Cook helpers, started Xvfb at 1400×900, launched the compiled R293 `rs.gui.Launcher` with `-Dspk.serverHost=127.0.0.1 -Dspk.serverPort=43594 -Dspk.offlineProbe=true`, and used Java Robot to select **Cook** on real Cooking range object ID **114**. The isolated synthetic server verified ISAAC-decoded client outbound packet **opcode 132, length 6**, world tile **(3362,4769)**, with a paired incoming synthetic **opcode 253**, object 114. The client reported legacy OSRS region **13386 / field1134** and the 3D game viewport was genuinely populated. All background test processes were cleaned up.

| Result | Fresh session 1 | Fresh session 2 |
| --- | --- | --- |
| Parent wrapper exit | 0 | 0 |
| GUI and timeline | PASS | PASS |
| Actual original cache files | 10,772 | 10,772 |
| Legacy OSRS region | 13386 / field1134 | 13386 / field1134 |
| World viewport nonblack fraction | 98.500% | 98.454% |
| Cook packet | opcode 132 / 6 bytes / object 114 | opcode 132 / 6 bytes / object 114 |
| Synthetic reply | opcode 253, matched object 114 | opcode 253, matched object 114 |
| 52-byte received wire SHA256 | `ba8fa895622fc1da562ab30908f71c1c58ae572c961a9b1fbbb56cea74541876` | `554593c9301b725b6abe74a0ef92c828467efb88988b7b7bb4e3a2818c32c501` |

**Independent evidence verifier: 204/204 checks PASS** including ZIP CRC, SHA manifest, exact R293 JAR identity, matching packet/ack, original local mock server event ordering, actual rendered PNG dimensions/crop, distinct ciphertext and screenshots, bounded timeline and cleanup, and missing/tampered source + existing-output denial.

### Private evidence deliverable

`SpawnPK_v309_R294_TWO_FRESH_R293_GUI_COOK_EVIDENCE_PRIVATE.zip` — **1,628,892 bytes**, SHA256 **`0950767449ec88e4b544d32125c8baed7ed06d8b58667ded56a7a374bef191bc`**, 34 ZIP members including manifest. Two deterministic independent ZIP builds are **byte-identical**. It includes the 2-session GUI images, synthesized local wire packets, receipt JSONs, original Linux client/server/robot logs, source-only replay script and evidence verifier; **no private compiled client JAR/classes, original game/cache files, full source tree, fonts, owner credentials, or installed game files**. Screenshots may depict private game content, so the evidence archive is **not uploaded to public GitHub**.

### Public, reproducible GitHub changes

- `tools/gui/r294/R294ReplayFromPinned.py`: exact original seven-archive SHA pins, enforces original R285 source member hashes, uniquely anchored R278→R293 JAR overlays, no-output overwrite, Linux/Xvfb only, localhost-only original bounded GUI protocol. Git blob SHA1 **`ff6a9e789cb148ed6d3a33861eedff39ea00857a`**, byte-identical to the *actual source used in fresh replay 2*.
- `tests/python/r294/R294SourceSafetyRegression.py`: **18/18** deterministic synthetic fixture tests, no private owner archives; Git blob SHA1 **`834ba7cf087b8cc24a6ba08c0c04e2342f9f3bf4`**, byte-identical to locally executed tests.
- `tests/python/r294/R294EvidenceVerifier.py`: **204/204** local real private GUI artifact checks; Git blob SHA1 **`a3c6bbacfee51a09fbdae6658f59a16bc0e8297d`**, byte-identical to local verifier.
- Existing Windows Server 2022 / Ubuntu 24.04 GitHub Actions source-only workflow now runs R294's 18-case **source-safety** suite. Hosted CI does *not* have R293 class JAR or private cache: a green CI cannot be cited as graphical gameplay verification; the private local two-session screenshots/socket evidence establishes that separately.

**Reproduction** (on an approved Linux test machine with the original archives and Xvfb/Pillow/Java11), place the seven exact original input ZIP/JAR files together, then use a fresh absent output path:

```bash
python tools/gui/r294/R294ReplayFromPinned.py --input-dir /path/to/pinned-owner-inputs --output /path/to/new-disposable-r294-home
```

The runner always uses 127.0.0.1 test port 43594 and the original source-owned synthetic server, never a live original game server.

## Remaining limitations / next direction

**Native Windows R293 GUI: NOT TESTED.** R292 Windows owner acceptance still pins the previous **R290** client, not R293. No original online server logic, real item production, authentication, complete gameplay, or sustained runtime validated. Do not change the original installed owner client or merge this DRAFT PR based on Linux evidence alone. Next meaningful task: native Windows R293 acceptance using this verified R293 binary and bounded synthetic localhost protocol or further concrete client-source defects.
