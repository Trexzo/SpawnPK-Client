# Chat 2 — notification subsystem R355

Exact client authority: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

- `rs/s/n/a` -> `CLIENT_CLASS_000935` -> `NotificationConfig`
- `rs/s/n/b` -> `CLIENT_CLASS_000936` -> `NotificationPlugin`
- `rs/s/n/c` -> `CLIENT_CLASS_000937` -> `Notifier`
- review: `SEMREVIEW_2EDCCBD4B007C877D722`

The config group is literally `notifications`.

The plugin subscribes to focus/chat/private-message events and produces alerts for exact
de-aggro, superior-spawn and private-message conditions.

The notifier backend posts `NotificationFired`, manages tray/native delivery, sound/beep,
focus/attention behavior, timeout state and screen-flash rendering.

R355 remains non-canonical semantic research only.
