# Chat 2 — Notifications identities R381

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/n/a` -> `CLIENT_CLASS_000935` -> `NotificationsConfig`
- `rs/s/n/b` -> `CLIENT_CLASS_000936` -> `NotificationsPlugin`
- `rs/s/n/c` -> `CLIENT_CLASS_000937` -> `Notifier`
- review: `SEMREVIEW_560F61FDFE4E438191E8`

## Exact/source join

The plugin retains the exact identity `Notifications`, notify/alert/notification tags,
focused/private-message/superior alert event handling and a dedicated configuration surface.

The config preserves RuneLite notification settings and descriptions while also adding
SpawnPK-specific alert toggles, so `NotificationsConfig` is intentionally descriptive
rather than claiming upstream `RuneLiteConfig`.

`rs/s/n/c` matches RuneLite `Notifier` structurally and behaviorally: tray/native
notifications, request-focus/flash handling, platform process delivery, notification sound
and `NotificationFired` publication.

## Withheld nested enum

`rs/s/n/c$a` remains unnamed. Exact v308 exposes NATIVE/OFF modes but no sufficiently
stable historical source identifier for this reduced nested enum.

R381 remains non-canonical semantic research only.
