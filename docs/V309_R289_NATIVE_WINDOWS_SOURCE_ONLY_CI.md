# SpawnPK v309 R289 — native Windows source-only CI acceptance checks

**2026-10-19. This is Windows safety-harness verification, not game-client Windows GUI verification.** Existing production-source R278, Linux/Xvfb R285 Cook packet proof, and R286/R288 owner-only native GUI tools are unchanged.

## Why this batch

R287 (read-only diagnostics) and R288 (guarded opt-in owner launcher) had only locally simulated or Linux-only checks. R289 adds a **real Windows-2022 GitHub Actions runner**, plus Linux, using only committed source files and disposable dummy fixtures. No owner-private archives or credentials are downloaded, game clients are not started, and the workflow has read-only repository permissions.

## Files

- `.github/workflows/v309-r289-windows-safety.yml` — Windows 2022 + Ubuntu 24.04 matrix, Python 3.11, unchanged line endings for SHA-pinned PowerShell/Python sources, read-only checkout, bounded jobs, runs 20 R287 regression cases and 13 R289 contract cases on each OS; runs a *native PowerShell* safety check only on Windows.
- `tests/python/r289/R289GateContractRegression.py` — independent source safety regressions: unchanged SHA-256 for R287/R288, required R286 launcher, GUI opt-in contract, hash verification ordering, no direct game launch, no private binary payloads, JSON rejection with empty owner inputs, and explicit Windows script success-exit hygiene.
- `tests/powershell/r289/Invoke-R289-SafeWindowsChecks.ps1` — parses existing R286/R288 PowerShell scripts on an actual Windows runner, verifies exact R288 launcher SHA, then executes R288 twice with **missing / deliberately invalid source ZIPs** and confirms explicit errors with **no output**. Executes R287 as a separate real Win32 Python process with no original archives, expecting refusal and authentic native Windows platform recognition. Does not pass `-RunNativeGui` or start the game.

## Observed test results and correction

The first Actions run `39269535827` passed **20/20 + 12/12** Python checks on Windows and Linux. The native PowerShell script also logged **17 passed checks** on Windows, but the job ended in failure because the deliberately rejected native Python child left a nonzero process exit value in the hosting shell even after all assertions passed. R289 corrected this by giving the standalone test runner an explicit `exit 0` after all assertions; the added 13th Python case guards against regressions in that fix.

The first Actions run is **not** a fully passing CI run. For final verification, consult the newest `v309 source-only Windows acceptance safety` workflow run associated with the latest PR #1142 head; never label native Windows CI successful until both matrix jobs show `success`. No owner-native graphical window, launcher integration against real private inputs, legacy-OSRS menu, authentic opcode132 Cook action, or sustained gameplay has been performed by this CI.

## Preservation and next gate

R287, R288 original release and script SHA pins remain unchanged; the R288 external release ZIP is still SHA256 `5824e59136c88296dffcfd7f6610556c5df68b1f889a2a606ac61a8cc83462c0`, and R288 PowerShell SHA256 is `7f7be191dbc01cc3e2117d6ed005c34abc68811112cacb993843f87ef9a4ba32`. Nothing installs or merges to `main`, and the private R278 client class JAR/cache stays local. Keep PR #1142 DRAFT.

The remaining key acceptance milestone is **real owner-machine R286 opt-in GUI receipt** after R288 preflight passes. CI checks are valuable risk reductions, not substitutions for that acceptance.
