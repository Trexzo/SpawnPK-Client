# Chat 2 R3 — exact-v308 PK quick-links panel R352

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R352 recovers the launcher-side PK/community quick-links panel and every behavior-bearing
button listener attached to it.

### Panel

- `rs/gui/e` -> `CLIENT_CLASS_000265` -> `PkQuickLinksPanel`

The panel visibly separates:

- server/community information links; and
- PK convenience commands.

Exact labels include:

- `Check these pages out for server information!`
- `Forums/Community`
- `Latest updates`
- `Price guide`
- `These commands will aid your PKing needs!`

### Command actions

The following listeners first require a live logged-in Launcher Client, then assign exactly
one literal command to `Client.ap`:

- `g` -> `EntangleCommandAction` -> `::entangle`
- `h` -> `MeleePotsCommandAction` -> `::pots`
- `i` -> `SaradominBrewCommandAction` -> `::brew`
- `j` -> `RestorePotionCommandAction` -> `::rest`
- `k` -> `RangingPotionCommandAction` -> `::range`
- `l` -> `MagicPotionCommandAction` -> `::mage`
- `p` -> `SpellbookSwitchCommandAction` -> `::switch`
- `q` -> `FoodCommandAction` -> `::food`
- `r` -> `VengeanceCommandAction` -> `::veng`
- `s` -> `BarrageCommandAction` -> `::barrage`
- `t` -> `TeleblockCommandAction` -> `::tb`

### External-link actions

- `m` -> `CommunityForumLinkAction`
- `n` -> `LatestUpdatesLinkAction`
- `o` -> `PriceGuideLinkAction`

Each action passes exactly one fixed SpawnPK URL to `Client.f(String)`.

### Withheld child

`rs/gui/f` is attached to the visible `Server rules` button but its exact-v308
`actionPerformed` method is empty. R352 therefore does not invent a semantic behavior
name for that no-op listener.

## Boundary

These are descriptive exact-v308 roles only. R352 is research-only and performs no
canonical acceptance or source rewrite.
