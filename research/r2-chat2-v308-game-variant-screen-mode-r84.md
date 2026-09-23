# Chat 2 — exact-v308 game variant / screen mode R84

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R84 is a separate non-canonical class-only semantic review batch for two strongly
self-identifying enums nested under R83 `ClientSettings`.

The other adjacent settings enums remain withheld because their exact nouns are less
certain even though their value sets are visible.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_190175A35620DE6C2C48`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/f/a$a` -> `CLIENT_CLASS_000168`
- `rs/f/a$c` -> `CLIENT_CLASS_000170`

## `rs/f/a$a` -> `GameVariant`

The enum contains exactly:

- `SPAWNPK`
- `RUNEX`

Each value also carries an exact display string:

- `SpawnPK`
- `Runex`

plus the associated site string.

R83 `ClientSettings` stores the active enum and derives variant-specific `spk` / `rx`
data-path naming from it. Launcher and the live UI shell use the selected display name for
window titles.

The enum also affects actual client logic rather than presentation alone. For example,
ObjectDefinition code branches on whether the current variant is `SPAWNPK` before applying
variant-specific loading behavior.

`GameVariant` therefore states the exact product/game selection role without asserting a
historical original identifier.

## `rs/f/a$c` -> `ScreenMode`

The exact enum constants are:

- `FIXED`
- `RESIZABLE`
- `FULLSCREEN`

R83 `ClientSettings` persists the enum under the exact key:

`screen_mode`

Its case-insensitive parser returns the matching enum and falls back to `FIXED`.

The type is consumed broadly by Client, the classic RSApplet/RSFrame shell, launcher/layout
code, interfaces and overlays when branching on fixed/resizable/fullscreen dimensions and
presentation.

That exact constant set + persistence binding + consumer surface fixes `ScreenMode`
strongly.

## Deliberately withheld sibling enums

R84 does not name:

- `rs/f/a$b` — `NORMAL`, `WINTER`, `DARK_WINTER`, `HALLOWEEN`, `SUMMER`
  plus color metadata;
- `rs/f/a$d` — `NONE`, `SPRING`, `SUMMER`, `HWEEN`, `DARK_WINTER`, `WINTER`.

Those two participate in the persisted `ground_mode` contract, but the exact distinction
between their nouns is not yet proven strongly enough to assign separate English class
names.

## Naming boundary

Both names are conservative semantic recovery names and are not claimed as verbatim
original developer identifiers.

## Acceptance boundary

Chat 2 does not promote R84. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_190175A35620DE6C2C48`.
