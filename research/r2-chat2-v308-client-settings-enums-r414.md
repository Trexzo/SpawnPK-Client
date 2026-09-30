# Chat 2 — exact-v308 client settings enums R414

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/f/a$a` -> `CLIENT_CLASS_000168` -> `ClientProduct`
- `rs/f/a$b` -> `CLIENT_CLASS_000169` -> `GroundMode`
- `rs/f/a$c` -> `CLIENT_CLASS_000170` -> `ScreenMode`
- `rs/f/a$d` -> `CLIENT_CLASS_000171` -> `SeasonalTheme`

Review: `SEMREVIEW_EF94F8616BF48BDC0E16`

## ClientProduct

Exact constants:

- SPAWNPK -> SpawnPK
- RUNEX -> Runex

Launcher and shared runtime configuration consume the active value for product branding and
the `spk` / `rx` runtime prefix. No public source preserving the original enum class
name was found, so `ClientProduct` is deliberately descriptive.

## GroundMode

Exact constants:

- NORMAL
- WINTER
- DARK_WINTER
- HALLOWEEN
- SUMMER

The value is the first component of the persisted setting:

`ground_mode=<mode>.<season>`

NpcDefinition, FloorDefinition and presentation paths branch on this value.

## ScreenMode

Exact constants:

- FIXED
- RESIZABLE
- FULLSCREEN

The exact persisted property is:

`screen_mode=<value>`

Client/Launcher/layout/rendering paths consume it directly.

## SeasonalTheme

Exact constants:

- NONE
- SPRING
- SUMMER
- HWEEN
- DARK_WINTER
- WINTER

This is the second component of `ground_mode=<mode>.<season>` and is independently
consumed by ItemDefinition/presentation overrides.

## Boundary

The massive parent `rs/f/a` settings class is not named in this batch because its original
source identity is not preserved strongly enough yet.

R414 remains non-canonical Chat 2 research.
