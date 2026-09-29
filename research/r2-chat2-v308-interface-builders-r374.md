# Chat 2 — exact-v308 interface builders R374

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/T` -> `CLIENT_CLASS_000566` -> `MonsterSpawnerInterface`
- `rs/n/c/U` -> `CLIENT_CLASS_000567` -> `PlayerIpUidMatcherInterface`
- `rs/n/c/Y` -> `CLIENT_CLASS_000571` -> `GameframeNavigationTabsInterface`
- review: `SEMREVIEW_B44F30D8077660195460`

## MonsterSpawnerInterface

Exact-v308 `rs/n/c/T` builds the root 41000 interface family.

Surviving visible strings include:

- `Monster Spawner`
- `Monster Selections`
- `Spawn this NPC`
- `Spawn x3`
- `Spawn distanced`
- `Toggle spawner`
- `You have selected: @yel@NPC Name`

The class is a pure interface builder registered centrally by `rs/n/d`.
No claim is made about server-side spawn permissions or behavior.

## PlayerIpUidMatcherInterface

Exact-v308 `rs/n/c/U` builds root 51200 and preserves the literal title:

`Player IP / UID Matcher`

It owns:

- IP Address / UID / Geolocation status text;
- 100 result rows;
- ONLINE / ONLINE (Non-match) result state;
- ordering by total matches / recent matches;
- `Search a new name`;
- `Ban all` / `Ban ALL`;
- per-result `Action` controls.

The semantic name follows the exact visible product title.

## GameframeNavigationTabsInterface

Exact-v308 `rs/n/c/Y` builds root 32000 from `gameframe/tab/*` assets.

Its five launcher actions are:

- Open achievement tab
- Open events
- Open pk ratings
- Open account information
- Open guides

It owns the selected/unselected gameframe tab sprites and arranges those launchers into one
compact navigation strip.

No historical source noun survives strongly enough to justify a narrower name, so the
descriptive `GameframeNavigationTabsInterface` label is used.

## Boundary

R374 is class-only, non-canonical semantic research. No acceptance or source rewrite is
performed.
