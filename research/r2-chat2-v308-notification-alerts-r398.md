# Chat 2 — notification alerts config/plugin R398

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/n/a` -> `CLIENT_CLASS_000935` -> `NotificationAlertsConfig`
- `rs/s/n/b` -> `CLIENT_CLASS_000936` -> `NotificationAlertsPlugin`
- review: `SEMREVIEW_89A04FE09DD9727AC9A1`

## Config surface

The exact config group is `notifications`.

Sections:

- `Alerts` — `Configure things that alert notifications`
- `Settings` — `The general settings for all notification alerts`

Exact config items cover:

- de-aggro timer;
- superior slayer/boss alerts;
- private messages;
- system tray icon;
- tray notifications;
- focus request policy;
- R244 `NotificationSound`;
- notification timeout;
- R397 `FlashNotification`;
- focused-client notification policy;
- flash color.

## Plugin behavior

`rs/s/n/b` extends the runtime plugin base.

Exact plugin descriptor:

- title: `Notifications`
- key: `notifications`
- tags: `notify`, `alert`, `notification`
- hidden: true

It injects R14 `Notifier` plus the config interface and subscribes to:

- `FocusChanged`
- `ChatMessage`
- `PrivateChatMessage`

Exact event-specific notifications include:

- `De-aggro timer reached!`
- `Superior spawned!`
- private-message notification text.

The class provides its config interface directly from ConfigManager.

## Naming boundary

These two SpawnPK-specific classes were not assigned an upstream RuneLite source identity.
The names are descriptive exact-v308 semantics.

Existing ownership remains unchanged:

- R14: `rs/s/n/c` -> `Notifier`
- R244: `rs/s/n/c$a` -> `NotificationSound`
- R397: `rs/e/n` -> `FlashNotification`

R398 remains non-canonical semantic research only.
