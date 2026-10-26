# SpawnPK v309 R288 — one-command guarded owner acceptance gate

**Implemented 2026-10-19; tested in Linux Python only. Native Windows/Win32 PowerShell execution and actual GUI gameplay remain NOT TESTED.**

R288 addresses the owner-workflow split introduced in R286/R287. An external source-only package plus one SHA-pinned PowerShell launcher now runs R287's full *read-only* environment and asset preflight; a GUI test is impossible without an explicit `-RunNativeGui` switch. The latter delegates to the **unchanged** original R286 guarded native-Windows runner, never directly to a game client.

## Release files and exact checksums

- `SpawnPK_v309_R288_OWNER_ACCEPTANCE_GATE_SOURCE_ONLY.zip`, **10,162 bytes**, SHA256 `5824e59136c88296dffcfd7f6610556c5df68b1f889a2a606ac61a8cc83462c0`. Its 5 ZIP entries are `MANIFEST.json`, `README.md`, the exact public R287 checker and 20-case R287 regression, and the new independent 13-case R288 release verifier. **No original/reconstructed game sources/JAR/classes, game cache, credentials, binaries, original fonts, screenshots or proprietary assets.**
- `tools/windows/Invoke-R288-Owner-Acceptance.ps1` as a separate no-manual-extract launcher, SHA256 `7f7be191dbc01cc3e2117d6ed005c34abc68811112cacb993843f87ef9a4ba32`, Git blob `5e1a815d857056563a129cb7aff8ba9978899279`. Source commits retain exactly the tested and distributed bytes.
- `tests/python/r288/R288ReleaseRegression.py` independently checks the zip including missing/added private file rejection, tampered source rejection, duplicate member denial, path safety, CRC/SHA manifest, true R287 Git blob hashes, and re-executes R287 from a new extraction.

## Validation and boundaries

**13/13 R288 suite passed** and **20/20 R287 regression passed from a clean extracted package**. Two deterministic ZIP builds yielded the identical release SHA256. The original R287 Java/Win32 visual probes are simulation seams in Linux tests, **not observed native Windows behavior**. No native Windows execution of PowerShell, unlocked desktop, Java window ownership, mouse click, or OSRS Cooking range interaction was performed in this milestone. Original R285 Linux/Xvfb Cook proof and R286 private client are unchanged.

The PowerShell gate verifies the source-only ZIP SHA, rejects absent/old R286 bootstrap (pinned final SHA256 `2186740003afb75df8dd79e2da6a721c121026733dc20ca087973f1d0cd70246`), extracts only trusted source scripts into a random scratch directory, and runs the SHA-pinned R287 readiness report. R287 verifies five exact owner archives and the original R286 ZIP; checks Python, Pillow, Java/JDK, 1400x900 100%-DPI primary desktop, safe absent output and free localhost 127.0.0.1:43594 port. An existing output is never overwritten; the script deletes only its own scratch source extraction.

Place both R288 files, both **final** R286 files, and the original five private archives in `Downloads`. For **read-only preflight** (the default, no game launch):

```powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Invoke-R288-Owner-Acceptance.ps1"
```

When the owner is ready for a real native GUI test, and *only then*, explicitly append `-RunNativeGui`. This invokes the original SHA-pinned R286 bootstrap with an isolated test home; the R286 runner independently repeats its own source, archive, window-ownership, and localhost-protocol checks. R287's readiness PASS alone is **never** GUI acceptance.

**Ownership:** Sole active v309 client chat, same draft PR #1142, issue #1117. No private source or cache is published, no production source changes since R278, no installed client modifications, no main merge. The next real evidence gate remains owner-native Win32 session results; fail-closed diagnostics must not be reinterpreted as gameplay success.
