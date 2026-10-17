# R213 — actual graphical startup probes and runtime fixes

Unlike prior offline-only tests, R213 executed the source-built R212 JAR under a Linux virtual display with the **server host explicitly set to 127.0.0.1**. It used the exact v309 non-game dependencies and owner-local resources from the pinned original JAR. This did **not** simulate successful gameplay or verify a complete graphical launch.

## Confirmed startup blockers
1. `TradingPostSearchPanel` expects `rs/plugins/tradepost/back_icon.png` and `fwd_icon.png`, but original v309 resources are `rs/s/u/*.png`. Both original bytes exist and map exactly.
2. `NotificationManager` expects `/icon.png`; exact original file is `assets/icon.png`.
3. `ObsidianSkin` expects `rs/ui/skin/RuneLite.colorschemes`; original resource is `rs/ui/c/RuneLite.colorschemes`.
4. `AssetVersion.getRemoteVersion()` caught network IO errors by constructing Swing labels off the EDT and dereferencing a null font, crashing the updater. Production Java source fix schedules error UI on Swing EDT, uses a fallback font and supports suppressing error dialogs in controlled offline tests. The changed Java class compiled under `javac --release 11` against the exact v309 source-built runtime.
5. `NotesPlugin` and other deobfuscated plugins load images relative to newly renamed packages. A private resource overlay uses **26 explicit original-to-renamed resource mappings** from the pinned original v309 JAR; 25 are backed by exact basenames, plus the original `profile_icon.png` to `profiles_icon.png` candidate. Original asset bytes are **not** included in the distributable.
6. **Remaining verified blocker:** `rs/plugins/configs/ConfigSidebar` requests `config_icon_lg.png` and that filename is not available in the original JAR. The virtual-display process still throws a plugin instantiation exception; do not claim successful startup.

The virtual display processes that returned exit code 124 were terminated by an explicit timeout; this **does not indicate a successful startup**. Before that timeout the logs documented deterministic resource/plug-in exceptions. Other background tasks may still query CloudFront asset endpoints, even though the game server host is pinned to localhost. The runtime is therefore **not fully offline**.

## Private result

`SpawnPK_v309_R213_RUNTIME_BOOTSTRAP_PRIVATE.zip` (SHA-256 `f023ce235161795cf93849e02d5b46cf94bb6818172ab053288c951b298c2a0e`) contains the complete R212 Java source with the single AssetVersion source fix, patch class JAR, unmodified R212 source-built client JAR, original v309 non-game library JAR, pinned local-resource Windows PowerShell overlay script and resource mappings, README and manifest. No proprietary font/image files bundled.

This is a **runtime bootstrap repair**, not a full reconstruction/runtime parity release. The R212 full Java11 compile and 10/10 offline test acceptance remain previous milestones; R213 does not claim another 1,275-source clean build. Fix missing config UI resources and perform a truly isolated GUI session before accepting runtime parity.

## Final integrated acceptance update

A second source fix changed `LoginScreen.field2051` from `ArrayList` to a `CopyOnWriteArrayList` to stabilize concurrent iteration of floating orbs during login startup. A clean, full **1,275-source** Java 11 compilation passed with **zero errors** and generated **1,376 classfiles**. The actual rebuilt JAR SHA-256 is `ddf83444eac151a659c95b75b39a392114ce71817381fa6cddc87881515798bc`.

Resource overlay mappings expanded to 32 owner-local mappings, including an explicitly disclosed fallback for `config_icon_lg.png`, plus the five PvP-tracker icons at the plugin's own resource paths. An 18-second virtual-display startup probe of the integrated R213 JAR found no fatal startup exception or `ConcurrentModificationException`, but was **terminated by timeout**. Logs still show missing optional loot icons and public asset/news endpoint lookup failures.

The same rebuilt JAR passed **10/10 offline checks**. The server-default configuration check was run without test-only `spk.serverHost` override; the other nine checks were run against a local-only host setting. These checks do not establish a fully successful graphical/gameplay launch.

Final private handoff: `SpawnPK_v309_R213_RUNTIME_BOOTSTRAP_PRIVATE_FINAL.zip`, verified ZIP SHA-256 `6c929dd90b8ba027542dcf29fb08521a07479a939793892e0fce4176f23fd91c`. Includes complete modified source, directly source-built client JAR, original-version *non-game* dependencies, 32 resource mapping paths and hash-checked PowerShell local overlay, tests, README and source manifest. No original font/image bytes are included.
