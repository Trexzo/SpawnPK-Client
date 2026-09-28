# Chat 2 — exact-v308 infrastructure and PvP Tracker semantics R12

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R12 remains a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or the R3-R11 review batches.

## Deterministic review result

- candidate classes: **15**
- resolved proposals: **15**
- unresolved: **0**
- review ID: `SEMREVIEW_655A5A8C14B6608179D9`
- field/method proposals: **0**

## Exact self-identifying/value classes

| Raw class | Stable ID | Candidate semantic |
| --- | --- | --- |
| `rs/e/c` | `CLIENT_CLASS_000147` | `ConfigStore` |
| `rs/e/h` | `CLIENT_CLASS_000152` | `ConfigItemDescriptor` |
| `rs/e/k` | `CLIENT_CLASS_000155` | `ConfigProfile` |
| `rs/e/m` | `CLIENT_CLASS_000157` | `ConfigSectionDescriptor` |
| `rs/j/b/b` | `CLIENT_CLASS_000309` | `CustomMenuEntry` |
| `rs/l/f/c` | `CLIENT_CLASS_000484` | `OverlayBounds` |
| `rs/l/f/f` | `CLIENT_CLASS_000487` | `OverlayMenuEntry` |
| `rs/ui/a/a` | `CLIENT_CLASS_001017` | `BoostInfoBox` |
| `rs/ui/a/j` | `CLIENT_CLASS_001026` | `TimerInfoBox` |
| `rs/ui/l` | `CLIENT_CLASS_001102` | `NavigationButton` |

Most of these carry exact self-identifying `toString` constants, including
`ConfigItemDescriptor(...)`, `ConfigProfile(...)`, `OverlayBounds(...)`,
`TimerInfoBox(...)`, `BoostInfoBox(...)` and `NavigationButton(...)`.

`ConfigStore` is role-based rather than a surviving identifier: exact bytecode proves a
file-backed key/value persistence layer using `Properties`, `ConcurrentHashMap`,
synchronized mutation, dirty tracking and file locking.

## Player Outline pair

- `rs/s/p/a` -> `PlayerOutlineConfig`
- `rs/s/p/d` -> `PlayerOutlinePlugin`

Exact evidence includes the config group `playeroutline`, options for outline color,
pet outline, feather and border width, plus the runtime title `Player Outline` and direct
runtime->config reference.

## PvP Tracker trio

- `rs/s/q/a` -> `PvPTrackerConfig`
- `rs/s/q/b` -> `PvPTrackerPanel`
- `rs/s/q/d` -> `PvPTrackerPlugin`

Exact evidence includes the `pvptracker` config group, filter/history options, panel strings
such as `Current Fight` and `Fight History (Filter by Usernames):`, and runtime creation
of a `NavigationButton` titled `PvP Tracker` using `pvp_icon.png`.

## Acceptance boundary

Chat 2 does not promote R12. Main/Core may accept any desired subset only through an explicit
`semantic_acceptance_spec` bound to
`SEMREVIEW_655A5A8C14B6608179D9`.
