# SpawnPK v309 R292 — truthful native-Windows readiness for the R290 client

**2026-10-19. Native Windows client GUI/graphics remain NOT TESTED.** R292 closes a specific owner-workflow defect, not a gameplay/transport/scene-implementation gap. All production client classes remain exactly **R290** (the one-class scene-hash/object-ID authority fix); no game code is committed here, no installed owner binaries changed, and PR #1142 remains DRAFT.

## Reproduced deficiency in R291

R291's `R291_PINNED_READ_ONLY_PREFLIGHT_PASS` meant seven original private file SHA checks, embedded R290 JAR and R286 overlay anchor authority passed. It did **not** check whether Java, javac, Pillow, a genuine Win32 1400×900 100%-DPI desktop, or localhost 127.0.0.1:43594 was available. Therefore the apparently green preflight could be printed on Linux or a non-compliant Windows desktop, only to fail when attempting the opt-in GUI run.

R292 preserves R291 as the **original immutable SHA-verified acceptance engine** and adds ten checks before calling it:

1. Pin/CRC of untouched public R291 source-only ZIP **and** the embedded R291 Python implementation.
2. Native `win32` platform.
3. R291's actual checks of all seven owner-private input files, R290 embedded client JAR, original R286 source pins and unambiguous overlay anchors.
4. Every output parent is free of symlink/reparse junctions (besides R291's original absent-output and archive-overlap safeguards).
5–8. Python 3.11+, actual Pillow ImageGrab import, `java` 11+ and `javac` 11+.
9. DPI-aware physical primary display **exactly 1400×900 at 96 DPI** (no fallback DPI guesses).
10. Ability to bind `127.0.0.1:43594` (the local test port).

**If ANY check fails:** R292 prints JSON `ready: false`, uses process exit 2, does not create an acceptance home, and does not start a client or server. A READY result remains **PREREQUISITES ONLY, NOT GAMEPLAY**. Native graphical run requires explicit `-RunNativeGui`, and the original R291/R286 test harness independently rechecks its own archive/GUI/window/local-port safeguards.

## Source-only release and verification

- `SpawnPK_v309_R292_WINDOWS_READINESS_GATE_SOURCE_ONLY.zip`: **17,086 bytes**, SHA256 **54e45ba2869f003b5377c8593172a5a90c3e7dfc73bd9aca12029f8d319d72fb**. Two deterministic byte-identical builds; **24/24** independent manifest/CRC/SHA/content/binary-exclusion/static checks.
- `Invoke-R292-Owner.ps1`: SHA256 **9ee44bc5b872526d9021762a59004efbb8c829ab74bd43882965dba5bb6caa9d**. A separate source-safe no-extract PowerShell bootstrap; SHA-verifies ZIP before extracting only authored scripts into a random scratch path.
- R292 ZIP bundles the **original unmodified R291 public-source ZIP**, pinned SHA256 `f932bd9d83b0ddb94f2373d5ba06f9aa65456a6d8b06c4b62f4616992fc0763a`. Thus **no separately staged R291 public-source ZIP** is necessary; seven existing private owner archives still needed for real positive preflight.
- `tools/windows/r292/R292-Owner-Readiness-Gate.py` and `tests/python/r292/R292AdmissionRegression.py` are committed byte-identical to the release/source-tested versions.
- `tests/powershell/r292/Invoke-R292-NativeSourceSafety.ps1` checks native Windows PowerShell parsing, fail-closed package hashes, and refusal when `-RunNativeGui` accompanies a tampered package, all without private original archives.

## Actual evidence versus tests

**Real owner-private inputs on Linux**: all seven SHA-pinned R291 inputs passed, R291 original public ZIP+Python loader passed, Python/Pillow/java/javac present; **R292 deliberately reported NOT READY** because Linux is not native Windows and native desktop/port claims cannot be made. No output home was created and no owner files modified. This directly demonstrates the R291 misleading-ready condition was corrected.

**Source-only deterministic:** 28/28 local Python admission regression tests PASS; GitHub Windows+Linux CI runs the same 28-case suite and native Windows PowerShell negative cases. A green Windows CI means only safety/default refusal paths are exercised: private owner archives and GUI actions **are absent** from hosted CI.

**No claims:** A passing R292 preflight does not establish real client rendering, actual Cook range click/packet, login, sustained session or original game-server cooking effects. Existing two **Linux/Xvfb** source-built R290 Cook opcode132/ack253 sessions remain valid, but are not Win32 evidence.

## Owner invocation

Keep exactly seven pinned original inputs and both **R292** release files in Downloads. No manual extraction.

Read-only prerequisites:

```powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Invoke-R292-Owner.ps1"
```

To attempt genuine Windows native GUI acceptance **only after** all prerequisites are met, append `-RunNativeGui`. The owner still must have an unlocked 1400×900, 100% DPI primary screen and a visible Java window at the fixed source-tested Robot coordinates.

**Next actual milestone:** owner-native R290 Java foreground-window and graphical Cook evidence with synthetic localhost packet receipt. Failures should be diagnosed from concrete owner logs instead of weakening hash, focus or geometry guards.
