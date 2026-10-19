# SpawnPK v309 — R286 guarded native-Windows acceptance preparation

**Verified 2026-10-19, Linux container only. Native Windows GUI acceptance is NOT YET TESTED.**

R286 does **not** rebuild or change the already verified owner-private v309 R278 client binary. It adds a separate, opt-in Windows GUI acceptance runner for the proven isolated OSRS-region Cooking range test. The test uses the earlier SHA-pinned R278 1,386-class Java 11-target client and *five original owner-private inputs*; the compiled client and original game cache are **not** distributed inside this package or published to GitHub.

## Windows acceptance protections

1. Exact SHA256 verification of all five original owner archives **before creating any output**. An existing output folder is never overwritten; missing inputs, bad hashes, unsafe output, missing parent, missing Python3.11+/Pillow or JDK compiler fail before launching GUI.
2. Refuses to run GUI on non-Windows platforms. Requires a real unlocked native Windows primary desktop, **exactly 1400x900 resolution and 100% DPI scaling**, and a free **127.0.0.1:43594** loopback port. The runner does not change screen resolution, scale or Windows policy.
3. Only creates a disposable private test home from your archives (10,772 cache assets), verified R278 class-JAR SHA256 `dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd`, and a resources-only original-JAR copy; it does **not** replace the installed client.
4. Real client Java AWT window must be the **visible foreground process owned by the Java child PID** immediately before any Robot mouse/keyboard sequence. If the owner is working in another window, it fails closed. The fixed-screen geometry still requires actual Windows acceptance; never rely on this test in an unrelated window.
5. Windows-native subprocess trees launched with `CREATE_NEW_PROCESS_GROUP`, separate logs, 95-second outer deadline and targeted `taskkill /PID <spawned PID> /T /F` for test descendants only. No global `taskkill /IM java.exe` or unrelated process kill.
6. The actual game-originated localhost receipt must contain a six-byte **opcode132** for real Cooking range **ID114** world **(3362,4769)**, authenticated selected legacy OSRS region **13386 (field1134)**, map-ready opcode121, and separately paired synthetic incoming **opcode253** reply. The original socket wire bytes and SHA256 are checked before a pass.
7. Produces `R286_acceptance.json`, `R286_run.log`, child-process logs, screenshots, decoded socket receipts, and a timeline in the **new output folder**. Nothing is merged into GitHub `main` or installed on the owner's PC.

## Executing on the Windows owner machine

First place the **R286 source-only evidence ZIP**, standalone `Invoke-R286-Guarded-Windows.ps1` bootstrap, and the five owner-private archives in one folder (or pass the input folder using `-InputDir`). The bootstrap has the exact R286 evidence ZIP SHA256 pinned, validates all private archive hashes and refuses existing output paths, extracts only authored test scripts into a disposable scratch folder, runs Python, and deletes that temporary scratch afterward. It requires Python3.11+ with Pillow, JDK11+ (JDK21 with `javac --release 11` recommended), and an unlocked Windows desktop at 1400x900 / 100% scale.

```
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Invoke-R286-Guarded-Windows.ps1 -InputDir "$env:USERPROFILE\Downloads"
```

Do not run the GUI test during unrelated interactive work: AWT Robot sends real clicks into the foreground game window. To verify your inputs without opening any GUI or creating a test home, add `-PreflightOnly`.

Direct runner (if the source ZIP has been extracted into a test-only folder):

```
python scripts/R286-Windows-Acceptance.py --r278 R278_PRIVATE.zip --r265 R265_PRIVATE.zip --assets ".spawnpk (4).zip" --original original-client.jar --r230 R230_PRIVATE.zip --output "C:\Users\...\Desktop\SpawnPK-R286-Acceptance"
```

**Current result:** Linux-only **19/19 harness safety regressions passed**, all five *real* owner input SHA256 hashes verified, a fresh 10,772-file private cache stage and the exact client class JAR checked, **two real Robot Java sources compiled with `javac --release 11`**, and R285 source-free prior Linux/Xvfb evidence independently re-verified **228/228 assertions**. The Windows code refuses GUI execution on Linux. **No Windows client window, mouse input, or runtime result exists yet.**

## Known limitations and rollback

This acceptance uses a synthetic 127.0.0.1 test server and dummy local login, not actual original game login/authentication, inventory, cooking mechanics, native server pathfinding or sustained production gameplay. UI positioning, Win32 foreground ownership, Java AWT behavior and process cleanup are **not yet empirically tested on Windows**. If the GUI run fails, `R286_acceptance.json` and logs identify the failing stage; only the newly created disposable output home can be manually deleted. Original source archives and installed client remain untouched.

Keep [`Trexzo/SpawnPK-Client` PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) DRAFT. No merge to main until real Windows acceptance and broader compatibility checks are completed.