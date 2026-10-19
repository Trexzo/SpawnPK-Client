# SpawnPK v309 R297 — owner-native Windows acceptance specifically for R295

**2026-10-19. Code and isolated staging verified; owner-native Win32 game GUI remains NOT TESTED.** Keep PR #1142 DRAFT; do not merge `main` or install over existing clients. No private original assets/source/JAR/classes uploaded to public GitHub.

## What was wrong with the prior acceptance path

R295 is the latest source-built production client (Scene.getHashAtTile bounds guard, JAR SHA256 `f5b6f4b6ea3e5e8fc49e1cbe61197647ed7c1e238a49d935c77882cb40da2e35`). R296 demonstrated two complete original-wait Linux/Xvfb graphical sessions, each sending real opcode132 Cook on range114 and receiving paired synthetic localhost opcode253. But the existing R291/R292 native Windows handoff **still targeted R290**; neither readiness nor a native Windows session from that handoff could establish R295 compatibility.

## R297 implementation, preserving authentic source authority

Two new *source-only* Python scripts:

- `tools/windows/r297/R297-Windows-R295-Acceptance.py` — byte-for-byte derived from the original R291 owner source with only exact R290→R295 private ZIP/JAR hash and path/identifier substitutions. It preserves the **original exact SHA-pinned R286 source verification**, original five owner inputs and R286 source ZIP; an additional **original private R295 release ZIP** is required. The embedded class-only R295 JAR is independently SHA-verified before staging and all R278/R290 binary selections are superseded. The original Windows foreground Java PID/window-bound checks, no guessed DPI, AWT Robot and isolated mock-server packet validation remain in force.
- `tools/windows/r297/R297-Owner-Readiness.py` — derived from the real R292 Windows admission code; loads the **SHA-locked R297 R295 GUI source** directly from its bundled sibling file. Reuses checks for all seven original owner input hashes, original source anchors, Python 3.11+, Pillow ImageGrab, Java/javac 11+, native Win32 with **1400×900 primary at 96dpi**, localhost port 43594, absent output, and nonreparse path ancestry. It returns JSON `ready:false` and exit **2** when any requirement fails. Default does **not** stage/launch anything; `--run-native-gui` is a deliberate explicit opt-in.

The existing `tools/windows/Invoke-R297-Owner.ps1` launcher verifies the published release ZIP by full SHA-256 **BEFORE** extracting only public authored code into a unique disposable scratch directory. It is read-only by default; `-RunNativeGui` propagates to the R297 Python worker only after the pinned package has been verified. No original owner file is modified; no live SpawnPK server is contacted.

## Actual verification against owner-private inputs (Linux)

All **seven** original pinned owner archives were locally available, including full R278/R265 source inputs, the authentic `.spawnpk (4).zip` cache, original client JAR/R230 assets, exact R286 source ZIP, and exact private R295 ZIP SHA256 `277fb5016d60e5b36bb22cede2b3b2500b9773636f433c65774db18a34e401f6`.

**Actual R297 read-only readiness:** source-hash checks, seven owner SHA inputs, original R286 source-anchor checks, Java, javac, Python and Pillow all PASS. The report returns **`ready:false`, process exit 2**, because the test was conducted on Linux rather than a genuine 1400×900 Win32 desktop; no local output created and no GUI run claimed.

**Actual source-verified private staging:** invoking R297's exact R286 staging routine in an isolated disposable Linux test home staged **10,772 authentic cache files**, inserted the exact **R295 class-only JAR** with SHA256 `f5b6f4b6ea3e5e8fc49e1cbe61197647ed7c1e238a49d935c77882cb40da2e35`, verified **neither R278 nor R290 client JAR was staged**, and compiled **two authentic Java 11 AWT helper classes** successfully. The entire disposable home was deleted after inspection. This is real source/cache/JAR staging and Java compilation, **not** a successful Windows GUI run.

**Public-only regressions:** `tests/python/r297/R297AcceptanceRegression.py` has **28/28 local tests PASS**, including exact SHA pins, trustworthy old-source retarget, no old R290 JAR acceptance, real Windows refusal, missing/tampered source, missing Java or Pillow, wrong display, unavailable localhost port, output safety, and explicit GUI opt-in. Native Win32 CI adds a PowerShell script parsing/hash/refusal/opt-in-negative-path suite. Hosted GitHub CI has no private binaries and does not establish actual graphical gameplay.

## Deterministic release

- `SpawnPK_v309_R297_R295_NATIVE_WINDOWS_SOURCE_ONLY.zip`: **20,289 bytes**, SHA256 **`661ea36616e8ffcd2612a1921257e4e70473030e42799c563bb57c7aea5dec93`**, 7 entries, two independently created byte-identical deterministic ZIP builds, **29** integrity/manifest/CRC/AST/binary-exclusion checks PASS. Contains only README, manifest, original public R291/R292 Python texts, new R297 Python texts, and test.
- `Invoke-R297-Owner.ps1`: SHA256 **`2259805542fdaef2c0ea48d2db83a766528ef0cb692b4a33c8bd7c41e275067f`**, stable Git blob `573e15c465a96b98050f0d9ac5a417714ba1cc75`.
- Exactly tested/packaged public source `R297-Windows-R295-Acceptance.py` Git blob `9ce5cb9e567abe582d76996dbf3a32e64baf6cb6`; `R297-Owner-Readiness.py` Git blob `d75c4937349503093f669947e21de3acbce0e9b0`; **28-case** R297 source regression Git blob `2f8d295dcc22e11cca7fe0e4ffbcd9fb5fa9fd63`.

## Owner invocation on Windows

Keep both R297 release files and the seven exact pinned original owner-input archives in Downloads. No manual extraction.

**Read-only check** (no owner game client opened):

```powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Invoke-R297-Owner.ps1"
```

For an intentionally consented native Windows R295 gameplay acceptance attempt only, append `-RunNativeGui`. It will create a fresh private test home only after all native display, PID, focus/Robot safety and SHA guards pass. It uses the bounded original R286 127.0.0.1 mock-server session: it does not establish actual authenticated live-server cooking/economy effects.

**Remaining:** actual **owner-native R295 Windows GUI** acceptance is still **NOT TESTED**, even if hosted Windows CI is green. Do not reinterpret Linux staging, simulated readiness or source-only CI as the missing native evidence.
