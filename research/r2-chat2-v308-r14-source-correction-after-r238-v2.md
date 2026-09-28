# Chat 2 — R14 source-identity correction after R238 (v3)

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Historical RuneLite source at `68c819924cfd6bfb4848c71f74c121109f289d5a` now resolves three older descriptive R14 labels:

- `rs/s/b/g` / `CLIENT_CLASS_000867`: `ConfigurationPlugin` -> `ConfigPlugin`
- `rs/s/b/w` / `CLIENT_CLASS_000883`: `PluginConfigurationRootPanel` -> `TopLevelConfigPanel`
- `rs/s/n/c` / `CLIENT_CLASS_000937`: `DesktopNotificationService` -> `Notifier`

## Notifier source fingerprint

Exact v308 `rs/s/n/c` and RuneLite `Notifier` share the same unusually distinctive responsibility bundle:

- injected Client / ClientUI / configuration / ScheduledExecutorService / EventBus dependencies;
- `NotificationFired` posting before delivery;
- notification focus policy;
- a 2000 ms flash lifetime with interaction-based cancellation;
- Linux `notify-send` delivery with TrayIcon fallback;
- macOS `terminal-notifier` detection and `osascript` fallback;
- the literal sender/group `net.runelite.launcher`;
- notification sound handling.

Exact v308 also preserves the highly identifying literals `terminal-notifier -help`,
`error sending notification`, and the AppleScript `display notification ... with title ...`
construction.

SpawnPK's class is locally pruned/adapted, so this does not claim byte identity. The source
noun `Notifier`, however, is substantially stronger than the earlier descriptive
`DesktopNotificationService`.

Proposal count remains **13**. No semantic acceptance is performed.

- previous corrected review: `SEMREVIEW_327683188A4DACD87309`
- source-corrected review: `SEMREVIEW_9BD6CC9F44F074203F9E`
- corrected proposal: `SEMPROP_71E663302D99CB1E890C`
