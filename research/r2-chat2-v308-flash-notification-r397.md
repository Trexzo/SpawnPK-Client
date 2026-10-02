# Chat 2 — exact-v308 FlashNotification R397

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/e/n` -> `CLIENT_CLASS_000158` -> `FlashNotification`
- proposal: `SEMPROP_42E8D473DA885CE4C625`
- review: `SEMREVIEW_7DCE9807CE1EFAE62993`

## Exact enum surface

The exact v308 enum constants are:

- `DISABLED` -> `Off`
- `FLASH_TWO_SECONDS` -> `Flash for 2 seconds`
- `SOLID_TWO_SECONDS` -> `Solid for 2 seconds`
- `FLASH_UNTIL_CANCELLED` -> `Flash until cancelled`
- `SOLID_UNTIL_CANCELLED` -> `Solid until cancelled`

## Exact notification integration

The notifications configuration returns this type from the exact config item:

- key: `flashNotification`
- title: `Flash`
- description: `Flashes the game frame as a notification`

R14 `Notifier` consumes the enum and implements the corresponding frame-flash lifecycle.
Two-second modes terminate after the fixed interval; until-cancelled modes remain tied to the
notification/focus lifecycle; FLASH modes alternate visibility while SOLID modes remain filled.

## Source identity

Historical RuneLite source uses the exact type name `FlashNotification` for the same
notification setting and the same five-mode surface.

R244 already owns the adjacent nested enum `NotificationSound`; R14 already owns
`Notifier`. R397 does not duplicate either authority.

R397 remains non-canonical semantic research only.
