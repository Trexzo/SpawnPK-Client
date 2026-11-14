# R386 — one-layer owner-private Windows full-source acceptance handoff

Repository: `Trexzo/SpawnPK-Client`. Stack base: R385 draft PR #1180.
**Source-M1 release gate CLOSED. KEEP DRAFT/UNMERGED.**

## Problem and bounded change

R385's full-source Windows verifier is ready, but the owner's computer is offline and the owner-private build kit is enclosed within several nested historical ZIP packages. R386 creates an **owner-private, single-layer offline bundle** with the exact, already-pinned R381 build kit and Linux reference JAR adjacent to the tools. It adds an offline Python acceptance orchestrator and a PowerShell entrypoint. **Zero of the 1,277 reconstructed Java source files change.**

The Python entrypoint checks the hashes of the private kit (`902e3b583840073c095ea51c5fe5bee4034340ab92bd19dc7c36f3173f092f96`) and reference JAR (`ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3`) and verifies SHA-pins for the inherited R383 compilation runner and R385 class comparator. It refuses preexisting output, missing files, symlinks and SHA drift. In a new scratch directory it compiles all 1,277 private Java sources using explicitly supplied JDK 21, checks the 1,388 class files and compares the class-only output JAR to the reference.

The Windows PowerShell wrapper detects an installed Adoptium JDK 21 or takes an explicit `-Java21Javac` path; it refuses non-Windows hosts, uses a uniquely named new output under `%TEMP%` by default, and exits successfully only for an actual Windows-local `R386_WINDOWS_FULL_BUILD_PASS` result.

A Linux pass is **separately labeled** `R386_LINUX_REHEARSAL_PASS` and can never be promoted to Windows acceptance. A class-byte or archive-metadata difference fails exact acceptance and retains local comparison evidence; nothing is automatically cleaned up.

## Tests performed, not inferred

- **23 public synthetic regression tests PASS locally**, checking true/false Windows claims, source and class count, dependency proofs, tampered private file hashes, tampered verification tools, symlink rejection and overwrite refusal.
- **Linux JDK 21 full real-source rehearsal PASS** from the R386 single-layer layout: 1,277 Java sources, both dependencies, 1,388 classes, exact reference JAR hash and zero changed classes.
- **Actual native Windows full-source compile: NOT PERFORMED**, because owner machine `DESKTOP-LTXXO4K` was offline at the time. Public Windows/Ubuntu CI uses synthetic inputs only, not the private Java sources.

## Private local execution

After extracting the private R386 ZIP on the **authorized Windows owner PC**, use PowerShell from within the extracted directory:

```powershell
& '.\tools\r386\Run-R386-Windows.ps1'
```

Optionally pass `-Java21Javac 'C:\Program Files\Eclipse Adoptium\jdk-21...\bin\javac.exe'` and a **new** `-NewOutputDir`. The result report is `R386-Offline-Acceptance-Result.json` inside the output directory. Do not upload the private kit, reference JAR, built classes, logs containing paths, or extracted source to a public repository.

## Remaining gates

No physical power-loss/directory durability guarantee, multi-file atomicity, safe staging deletion, original-v309 binary parity, actual GUI/game login, v312 compatibility or production acceptance has been demonstrated. R386 never launches the client or updates the live v312, updater, user caches, original v309 JAR or server.
