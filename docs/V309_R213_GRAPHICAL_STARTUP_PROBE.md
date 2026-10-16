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
