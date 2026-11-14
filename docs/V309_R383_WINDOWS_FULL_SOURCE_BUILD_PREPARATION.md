# R383 — full-source Windows build acceptance, offline preflight

**Correct repo:** `Trexzo/SpawnPK-Client`; stacked on R382 draft PR #1177. Keep **DRAFT / UNMERGED**, private source gate CLOSED.

## Windows blocker

The authorized remote PC `DESKTOP-LTXXO4K` was **offline** at the R383 preflight (2026-11-14). A genuine **Windows full 1,277-source compilation has NOT been performed**, so this work MUST NOT be presented as completed Windows acceptance. Earlier R382 tested 10 exact recovered Java sources in 15 isolated Windows fixture scripts, not the full corpus. Do not confuse the two.

## Real private baseline and Linux reference validation

- Input: owner-private R382 complete delivery SHA256 `9f21f71d070ab67ea50baed259bb13a8ae477eb2cee75236809128240a1169b3`.
- Nested R381 private package SHA256 `67cf1940f1332d445d9e485424b85ceff3cafd76dbbafddcca16b4f1019c52db`.
- Nested reproducible kit SHA256 `902e3b583840073c095ea51c5fe5bee4034340ab92bd19dc7c36f3173f092f96`.
- Revalidated 1,277 source hashes and 2 exact dependency JAR hashes. Source changes: **zero**.
- Local Debian/OpenJDK21 full compile **1,277 Java sources → 1,388 classfiles**. Existing private rebuild script and the new cross-platform R383 runner independently reproduced JAR SHA256 `ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3`.
- The new runner was exercised with a workspace containing spaces. It uses quoted `javac @sources.arg` paths and `--release 11 -proc:none -g:none`, refuses existing outputs, requires JDK21, verifies source/dependency SHA manifests, and checks class count and output JAR digest.
- On Windows, actual output must be generated locally with the runner and inspected. If the bytes differ, stop; record the divergence rather than claiming acceptance.

## Owner-PC command (only after PC is online)

Extract the **private R383 ZIP locally** to a scratch folder on the authorized Windows PC, not under production `fullspkclient`. In PowerShell:

```powershell
& '.\tools\r383\run_on_windows.ps1' -PrivateBundle '.\PRIVATE-R382-Complete-Windows-Acceptance.zip'
```

If necessary pass `-Python` and `-Javac` with the installed Python 3.12 and Temurin JDK21 paths. It checks input SHA and writes a *new* `SpawnPK-R383-Windows-Offline-Results` directory with `R383-Verification-Report.json`, a compiler log and a source-built JAR. No client is launched. A Windows pass is only authentic when the result reports `R383_WINDOWS_PRIVATE_FULL_BUILD_PASS` on `os.name == 'nt'` and the exact expected hashes and counts. Existing output directories are never overwritten.

## Public PR scope

Only the cross-platform runner, PowerShell launcher, generic javac synthetic probe, 24+ synthetic validation tests, SHA witness, CI workflow and report. GitHub Actions **never has the private source or dependency JARs** and only proves the public synthetic contract.

## Unproven

No full Windows source build until owner PC is online, no original-v309 binary parity, GUI/login/reconnect, real cache migration, v312 compatibility, power-cut durability, multi-file atomicity or source-publication approval. No v312/updater/server/cache modifications.
