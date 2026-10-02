# Chat 2 — source-identified config core R399

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R399 recovers eleven exact source identities from the shared config framework:

- `rs/e/a` -> `CLIENT_CLASS_000145` -> `Alpha`
- `rs/e/b` -> `CLIENT_CLASS_000146` -> `Config`
- `rs/e/d` -> `CLIENT_CLASS_000148` -> `ConfigDescriptor`
- `rs/e/e` -> `CLIENT_CLASS_000149` -> `ConfigGroup`
- `rs/e/f` -> `CLIENT_CLASS_000150` -> `ConfigInvocationHandler`
- `rs/e/g` -> `CLIENT_CLASS_000151` -> `ConfigItem`
- `rs/e/i` -> `CLIENT_CLASS_000153` -> `ConfigManager`
- `rs/e/l` -> `CLIENT_CLASS_000156` -> `ConfigSection`
- `rs/e/o` -> `CLIENT_CLASS_000159` -> `Range`
- `rs/e/p` -> `CLIENT_CLASS_000160` -> `RequestFocusType`
- `rs/e/q` -> `CLIENT_CLASS_000161` -> `Units`

Review: `SEMREVIEW_53EE5FBF1CEB1A7A1FB2`.

## Source-map authority

The recovered semantic map names these exact classes under `rs.config.*`. Exact-v308
bytecode then independently confirms the corresponding RuneLite config API contracts.

Examples:

- `ConfigDescriptor` stores ConfigGroup + section/item descriptor collections.
- `ConfigInvocationHandler` is the dynamic-proxy InvocationHandler and contains the exact
  diagnostics about missing `@ConfigItem` / `@ConfigGroup`.
- `ConfigManager` owns ConfigStore + ConfigInvocationHandler and implements config proxy,
  get/set/unset, serialization, save and descriptor construction.
- `ConfigItem` exposes position/keyName/name/description/hidden/warning/secret/section.
- `ConfigSection` exposes name/description/position/closedByDefault.
- `Range` exposes min/max.
- `Units` preserves MILLISECONDS, MINUTES, PERCENT, PIXELS, SECONDS and TICKS.
- `RequestFocusType` is the focus policy consumed by NotificationsConfig/Notifier.

## Already-owned siblings

R399 does not duplicate:

- R12 `ConfigStore`
- R12 `ConfigItemDescriptor`
- R12 `ConfigProfile`
- R12 `ConfigSectionDescriptor`
- R397 `FlashNotification`

## Deliberate exclusion

`rs/e/j` has the exact three-method `key/name/position` contract expected of RuneLite
`ConfigObject`, but the recovered semantic source map omits this class. R399 leaves it
unproposed rather than silently elevating structural resemblance to source identity.

R399 remains non-canonical semantic research only.
