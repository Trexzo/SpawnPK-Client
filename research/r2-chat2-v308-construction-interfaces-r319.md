# Chat 2 — exact-v308 construction interfaces R319

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/x` -> `CLIENT_CLASS_000677` -> `ConstructionBuildOptionsInterface`
- `rs/n/c/y` -> `CLIENT_CLASS_000678` -> `ConstructionBackgroundInterface`
- review: `SEMREVIEW_04FD79B45379F4F5FCB5`

R2 already owns sibling:

- `rs/n/c/z` -> `CLIENT_CLASS_000679` -> `ConstructionRoomSelectionInterface`

That existing recovery is important because it proves `x` is not the 23-room selector.

## ConstructionBuildOptionsInterface

Exact root:

- 39982

Exact background child:

- 39981 -> `construction/sprite 1`

The interface builds eight repeated option groups. Each group contains:

- `Name1` ... `Name8`
- `lvl1` ... `lvl8`
- up to four requirement rows:
  - `Req1.1` etc.
  - `req2.1` etc.
  - continuing through option 8

The groups are arranged in two columns across the construction panel.

The placeholders are deliberately generic, so this batch does **not** claim a narrower noun
such as furniture, hotspot object, room object or fixture. The exact role proven by layout is
construction build-option selection plus level/resource requirements.

## ConstructionBackgroundInterface

Exact root:

- 39984

Only child:

- 39983 -> `construction/sprite 0`

The class owns no labels, actions, requirements or mutable packet state. Its entire interface
surface is the construction background/root image.

## Cross-corpus corroboration

Independent exact-client construction research already established:

- construction as a POH / player-owned-space subsystem;
- explicit server-controlled build mode;
- a separate 23-room catalogue in `rs/n/c/z`;
- ordinary widget interaction for construction choices.

The same research warns that client-side construction values can be stale/presentation-only,
so R319 makes no server-authority claims.

## Boundary

Names are descriptive exact-v308 behavior names only. No original stripped developer names
are claimed. R319 remains non-canonical semantic research.
