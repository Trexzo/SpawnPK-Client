# R315 — 110-second authentic GUI test and verified GitHub handoff

**2026-10-26** · Complete private recovered **SpawnPK v309** Java client, distinct from the exact original-v311 bytecode recovery project. Baseline R311 production code unchanged.

## Original client runtime acceptance

Two independent full-client sessions used the exact owner's original cache bundle (**10,772** files) and v309 resources-only JAR with a localhost-only synthetic ISAAC game server and Linux/Xvfb graphical desktop:

| Observable | First replay | Second fresh replay |
|---|---:|---:|
| Real GUI and client final checkpoint | 110.16 s | 110.25 s |
| GUI Cook mouse actions | 3 | 3 |
| Actual client ISAAC-decoded opcode132 / object114 actions | 3 | 3 |
| Matching synthetic server opcode253 responses | 3 | 3 |
| Outgoing wire bytes | 152 | 151 |
| Client outgoing wire SHA-256 | `5c4dab0a10cebc64d8bf597d1030e44d222284e33e876c07912070acc155012f` | `08ec27fd280a9e0f6db69dac28c0732230fdd893caa4f8845d61dd9105a1b443` |
| Private fixture reported PASS / all children cleaned | yes | yes |
| Top-level packaged-runner exit 0 | No: initial verifier expected 5 rather than 7 child processes | Yes |

The initial session's *actual GUI fixture* ended cleanly after 110.16 seconds and its receipt passes the corrected independent verifier, but the outer wrapper initially exited 1 because it still expected five cleanup records from the older two-action test. R315 spawns seven child processes (login + three action robots + walk robot + client + server), and the corrected verifier requires seven. The second fully separate run exited **0** after 110.25 seconds.

The third successful client action was decoded/acknowledged at approximately 86 seconds. Authentic rendered scene region **13386 (field1134)** was visible, with images captured at 40, 55, 70, 75, 95 and 110 seconds and original client/server alive at last checkpoint.

**Negative evidence: movement NOT_VERIFIED.** A real AWT walk click was sent, but the client emitted no verified opcode-164 walk packet to the localhost server; no authoritative movement acknowledgment was observed. No NPC/inventory action was tested in this release. This is **not production-server authenticated gameplay** or a native Windows GPU certification.

## Exact full-tree source and regressions

All **1,277 recovered Java source files** are still unchanged and compile with Java 11 target to **1,386 classes**. Rebuilt JAR SHA-256 is **`b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721`** — identical to R311–R314. All **2,703/2,703** inherited actual compiled-client regression assertions pass. No new production Java code is claimed.

Cumulative private archive `SpawnPK-v309-R315-Full-Recovered-Source-Private.zip` is **24,339,390 bytes**, SHA-256 **`e46a213ba949dc0a2f420a040b5c9d38451c0923e3ea39917a5d2eb3c9b2fa28`**. It includes complete recovered Java, private compile dependencies, compiled original-derived JAR, tests/fixtures, exact source-file SHA manifest and two real local GUI run receipts/screenshots; no original 203 MB cache, v309 original resource JAR or real account material.

## GitHub location — important distinction

- **Public:** [Draft PR #1143](https://github.com/Trexzo/SpawnPK-Client/pull/1143) contains source-safe recovery recipes, original-independent CI tests and redacted reports. It does **not** contain private game source or owner cache.
- **Private:** [Trexzo/fullspkclient-private / recovery/v309-r315-world-acceptance](https://github.com/Trexzo/fullspkclient-private/tree/recovery/v309-r315-world-acceptance/recovery/v309-r315) now holds a strict real replay receipt validator, a pinned PowerShell synchronization script, and a private recovery README.
- **Still pending:** the GitHub connector only supports writing supplied text/blob contents; it cannot directly transfer the 24.3 MB container archive or all 1,277 Java files. **The entire source tree is not yet uploaded to private GitHub.** The owner-private [SHA-pinned sync script](https://github.com/Trexzo/fullspkclient-private/blob/recovery/v309-r315-world-acceptance/recovery/v309-r315/Sync-R315-FullRecoveredSource.ps1) is committed and will copy and push the complete source into the isolated private branch from an authenticated local clone. Do not claim GitHub contains all the code until that import actually succeeds.

The private git branch was created without modifying its other owner-development files or merging anything. The distinct original-v311 source-parity lane remains untouched. Keep PR #1143 **DRAFT/UNMERGED** and preserve strict real-world and native Windows release gates.
