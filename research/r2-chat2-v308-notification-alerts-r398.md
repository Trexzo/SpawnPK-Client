# Chat 2 — notifications config/plugin R398

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Corrected source identities

- `rs/s/n/a` -> `CLIENT_CLASS_000935` -> `NotificationsConfig`
- `rs/s/n/b` -> `CLIENT_CLASS_000936` -> `NotificationsPlugin`
- review: `SEMREVIEW_74CB0B5998688D24E634`

The first R398 draft used descriptive labels `NotificationAlertsConfig` and
`NotificationAlertsPlugin`. A stronger recovered semantic source map subsequently fixed the
exact source identities as `NotificationsConfig` and `NotificationsPlugin`, so the batch was
corrected before relying on the descriptive names downstream.

## Exact-v308 corroboration

`NotificationsConfig` uses config group `notifications` and owns alert/settings surfaces
for de-aggro, superior spawn, private messages, tray, focus, R244 NotificationSound, timeout,
R397 FlashNotification, focused-client notification policy and flash color.

`NotificationsPlugin` has runtime descriptor title `Notifications`, key `notifications`,
tags `notify` / `alert` / `notification`, injects R14 Notifier and NotificationsConfig,
and subscribes to FocusChanged, ChatMessage and PrivateChatMessage.

Existing ownership remains unchanged:

- R14: `rs/s/n/c` -> `Notifier`
- R244: `rs/s/n/c$a` -> `NotificationSound`
- R397: `rs/e/n` -> `FlashNotification`

R398 remains non-canonical semantic research only.
