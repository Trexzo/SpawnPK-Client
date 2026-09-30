# Chat 2 — RuneLite configuration framework R412

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R412 recovers the source identities of the embedded RuneLite configuration framework:

- `rs/e/a` -> 000145 -> `Alpha`
- `rs/e/b` -> 000146 -> `Config`
- `rs/e/c` -> 000147 -> `ConfigData`
- `rs/e/d` -> 000148 -> `ConfigDescriptor`
- `rs/e/e` -> 000149 -> `ConfigGroup`
- `rs/e/f` -> 000150 -> `ConfigInvocationHandler`
- `rs/e/g` -> 000151 -> `ConfigItem`
- `rs/e/h` -> 000152 -> `ConfigItemDescriptor`
- `rs/e/i` -> 000153 -> `ConfigManager`
- `rs/e/j` -> 000154 -> `ConfigObject`
- `rs/e/k` -> 000155 -> `ConfigProfile`
- `rs/e/l` -> 000156 -> `ConfigSection`
- `rs/e/m` -> 000157 -> `ConfigSectionDescriptor`
- `rs/e/n` -> 000158 -> `FlashNotification`
- `rs/e/o` -> 000159 -> `Range`
- `rs/e/p` -> 000160 -> `RequestFocusType`
- `rs/e/q` -> 000161 -> `Units`

Review: `SEMREVIEW_D720B25EE5B61C0B9400`

## Source-identity evidence

These are not merely descriptive guesses. Exact-v308 bytecode preserves the same type
relationships, annotation targets/defaults, descriptor composition and literals as RuneLite's
public `net.runelite.client.config` sources.

Particularly strong surviving identities include:

- `ConfigProfile(id=..., name=..., sync=..., active=..., rev=...)`
- FlashNotification constants:
  - DISABLED
  - FLASH_TWO_SECONDS
  - SOLID_TWO_SECONDS
  - FLASH_UNTIL_CANCELLED
  - SOLID_UNTIL_CANCELLED
- RequestFocusType constants:
  - OFF
  - REQUEST
  - FORCE
- Units constants:
  - ms
  - mins
  - %
  - px
  - s
  - ticks
- ConfigData's ConcurrentHashMap/Properties persistence and atomic file replacement contract.

## Boundary

Top-level `rs/e` and its record `rs/e$a` are unrelated to this RuneLite config package
despite sharing the obfuscated package prefix and remain unnamed.

R412 remains non-canonical Chat 2 semantic research.
