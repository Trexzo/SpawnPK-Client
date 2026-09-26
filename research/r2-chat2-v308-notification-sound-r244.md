# Chat 2 — exact-v308 NotificationSound R244

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R244 is a separate non-canonical class-only review for the notification-sound mode consumed by the reviewed notification configuration/service family.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_0AC800944F9BC39C0F26`
- field/method proposals: **0**

## Stable ID

`rs/s/n/c$a` -> `CLIENT_CLASS_000938` -> `NotificationSound`

The stable slot is fixed by the contiguous exact-v308 class lineage:

- `rs/s/n/a` -> `CLIENT_CLASS_000935`
- `rs/s/n/b` -> `CLIENT_CLASS_000936`
- `rs/s/n/c` -> `CLIENT_CLASS_000937`
- `rs/s/n/c$a` -> `CLIENT_CLASS_000938`
- compiler switch-map helper `rs/s/n/d` -> next slot
- `rs/s/o/a` starts at `CLIENT_CLASS_000940`

## Exact configuration binding

Reviewed `NotificationAlertsConfig` exposes config key `notificationSound`, title `Notification sound`, and returns this exact enum type.

Exact v308 preserves two constants:

- `NATIVE("Native")`
- `OFF("Off")`

The enum's `toString()` returns that display label.

Reviewed `DesktopNotificationService` consumes the same enum in its live sound-notification branch.

## Source identity

RuneLite's notification configuration uses the source type name `NotificationSound` for the `notificationSound` setting. That independently fixes the source noun, while the exact v308 bytecode fixes the local variant's two-mode surface.

Confidence is **0.998** because the source identity and runtime role agree, while contemporary RuneLite contains an additional CUSTOM option not present in this v308 variant.

## Acceptance boundary

R244 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
