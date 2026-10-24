# v309 R291 — R290-specific native Windows acceptance, guarded owner-only

**2026-10-19: new Windows acceptance *implementation* complete, private authentic-asset staging and Java11 AWT helper compilation verified on Linux; native owner-Windows graphical interaction remains NOT TESTED.** Keep PR #1142 DRAFT and leave the installed client untouched.

## Why R291 was needed

R286/R288 owner acceptance explicitly staged the **previous R278** private class JAR. Those harnesses cannot establish Windows acceptance for the R290 production client fix. R291 extends that exact SHA-pinned original R286 harness through a **small, strict, source-only overlay**, which changes only the selected class-only client JAR to R290 while preserving all original synthetic localhost verification and authentic cache staging. It refuses unknown or duplicated replacement anchors and invalid original source bytes. It does **not** rewrite the private original archives, change server addresses, bypass authentication or install on the owner PC.

The R291 overlay also tightens two GUI safety boundaries: it fails closed when Windows system DPI cannot be confirmed (the R286 fallback previously guessed 96 DPI), and demands the real foreground Java client window contain the full expected fixed Robot click/viewport coordinates before sending AWT input. The original 1400x900 at 100%-DPI desktop requirement remains intact. This may reject an otherwise workable monitor/window arrangement; never weaken this gate without actual owner-native geometry evidence.

## Input pins and build identity

The input directory must contain **seven exactly named, original SHA-pinned inputs**: five owner originals (R278 private source-built package, R265 source/dependencies, `.spawnpk (4).zip` with 10,772 cached files, original `client(20261015-104312).jar`, R230 original assets), plus original R286 source-only acceptance ZIP and R290 private build ZIP. Input SHA-256 hashes are embedded in the open-source verifier and checked before any staging.

- Original R286 public-safe ZIP SHA256 `2cacd2c551d6169be45e695f324d6c70a6d2a0b73a59b15fc5bce444f88a9877`
- Original private R290 package SHA256 `3bb467029ec552f7345a054dbed7ee8da2ef646bdfa2ce72707ce384b646f41c`
- Embedded reconstructed R290 class-only JAR SHA256 `f2f914f12196705fd7233ea022742157d13deb50be85289465ce26b0dde3cd4a`
- Release `SpawnPK_v309_R291_R290_NATIVE_WINDOWS_SOURCE_ONLY.zip` SHA256 **`f932bd9d83b0ddb94f2373d5ba06f9aa65456a6d8b06c4b62f4616992fc0763a`**, 8,520 bytes, four ZIP entries (three source/readme plus manifest). Two byte-for-byte identical deterministic release builds. No client Java/class/JAR, proprietary cache/assets, fonts, screenshots or original login details.
- Standalone no-extract `Invoke-R291-Owner.ps1` SHA256 `91b7f02a5985c37c43f1ad1c8917c407eb56fd213398f4fce0e0e4f6249ebacc`.

## Executing without a manually extracted package

Place the **two R291 release files** (source-only ZIP and PowerShell bootstrap) and **all seven original input files** together, normally in `Downloads`. The PowerShell bootstrap checks the source-only ZIP hash, extracts *only author-written scripts* into a unique disposable scratch directory, and removes that scratch on completion. The Python worker individually checks all seven input hashes, R290 embedded JAR SHA, exact original R286 source SHA and anchor uniqueness, and refuses existing, symlinked, unsafe or missing output directories. By default it **does not launch the client or create a test home**.

Read-only integrity check:

```powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Invoke-R291-Owner.ps1"
```

For an **explicit, intentional real native-Windows graphical test**, append `-RunNativeGui`. This creates an isolated owner-private test home and sends AWT clicks only after foreground Java client-PID, window-boundary, desktop and localhost checks pass. It requires the exact original input archives: simulated sample files will not satisfy checks.

## Actual evidence, clearly separated

- **Actual owner-private assets:** seven original archives verified byte-for-byte by SHA256, including the 3.57 MB R290 package; R290 private JAR internal SHA256 matched.
- **Actual patched harness staging (Linux only):** used exact R286 source ZIP and exact R290 class JAR; `verify_inputs` accepted all six original+R290 private inputs; staged **10,772 real cache files** into a new temporary test home, compiled **two Java11-target AWT helpers**, and confirmed only `R290_SOURCE_BUILT_CLASS_ONLY.jar` was staged—no old R278 client JAR.
- **Offline source-only regression:** 23/23 cases PASS on Linux, covering all required pins, known anchors, exact R290 retarget, read-only CLI, fake archive failure, output refusal, wrong embedded JAR, script tampering, path traversal and no Windows GUI launch off Windows.
- **R290 prior graphical evidence:** two genuine Linux/Xvfb client UI/local mock-server Cook op132 + synthetic reply253 passes from R290; *not* a Windows pass.
- **GitHub native Windows CI:** source-only unit and PowerShell safety tests do not have private input archives, so they cannot claim genuine owner-graphics acceptance.

The original R286 launcher/caches, original R278/R265 archives, and existing installed Windows client are never modified. Nothing merged to `main`.

## Next acceptance gate

On the owner machine, the R291 wrapper must use a real interactive native Windows desktop, perform foreground PID + window coordinate validation and reproduce authentic legacy OSRS region13386/field1134, Cooking range114, outgoing opcode132 six-byte interaction at world(3362,4769), and independent localhost synthetic opcode253 reply. A failure must be reported as a failure, with private logs and screenshots retained locally; do not reinterpret source-only tests as runtime proof or disable guards to force a pass.
