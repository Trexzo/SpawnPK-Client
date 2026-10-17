# Chat A R243–R246 campaign: measured verification and acceptance boundary

Executed on 2026-10-17 against canonical private R242 source (R234 cache helper retained without production edits).

## R243 actual Linux build / regression
- JDK 21 javac `--release 11 -proc:none -g:none`: **1,277 real Java sources**, **1,386 classfiles**, **0 compiler errors**; independent recompilation of R242 baseline.
- **19/19 compatible regressions exit 0**, with **18 substantively exercised on Linux**; Windows-specific R228 alias regression exits NOT_APPLICABLE and is NOT native Windows acceptance. Two incompatible Lane B-only downloader tests excluded.
- No production source changed in this verification batch.

## R244 source-level protocol audit (not runtime auth)
18/18 structural checks of canonical Client.java/Configuration.java: handshake 14, name hash, server seed, RSA login payload, opcodes 16/18, 9 cache revision ints, paired ISAAC state, login response 2 plus two following bytes, finishLogin local-player initialization, post-success opcode 185, explicit host/port controls. Real successful authenticated localhost session and game-world synchronization remain unverified.

## R245 original-source recovery integration gate
Do NOT overwrite this runnable private source with standalone source-only #1114: Packet proof claims 81/81 methods, 2,296 instructions in a distinct Java9 closure, and must be reviewed for exact source/provenance/method dependencies before isolated integration. Original-equivalent whole tree milestone #1004 remains open.

## R246 PR scope / release gate
#1084 is draft and contains no public production Java in the changed-file list; hosted synthetic CI is not proof of private full build. Cache R234 reviews #1127 and #1128 are duplicate evidence for the same handoff already adopted privately by R242. Consolidate only after verifying ancestry and preserving evidence, not through bulk blind merges.

## Remaining
Native Windows asset/GUI/cache tests; protocol-aware local authenticated world entry (not code 2 alone); original v309 full source-only parity, redistribution authorization. Retain draft and don't claim gameplay or native Windows pass.
