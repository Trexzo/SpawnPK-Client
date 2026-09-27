# Chat 2 — exact-v308 self-identifying interface frontier R291

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/D` -> `CLIENT_CLASS_000549` -> `DuelPresetLoadInterface`
- `rs/n/c/G` -> `CLIENT_CLASS_000552` -> `ItemEnchantmentChestInterface`
- `rs/n/c/U` -> `CLIENT_CLASS_000567` -> `PlayerIpUidMatcherInterface`
- `rs/n/c/p` -> `CLIENT_CLASS_000669` -> `ClanSetupInterface`
- `rs/n/c/s` -> `CLIENT_CLASS_000672` -> `ClanWarsSetupInterface`
- `rs/n/c/v` -> `CLIENT_CLASS_000675` -> `CollectionLogInterface`
- review: `SEMREVIEW_065EC031D6C95C0ADEAB`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 identity

These classes were selected because their surviving UI text/resources identify the interface role directly rather than by package adjacency.

`DuelPresetLoadInterface` preserves **Load last duel**, **Load last rules** and the `misc/duel load` resource.

`ItemEnchantmentChestInterface` preserves the exact title **Item Enchantment Chest** and the complete enchantment flow: categories, selected item, ingredients, success chance, attempt, preparation, success and failure.

`PlayerIpUidMatcherInterface` preserves the exact title **Player IP / UID Matcher**, IP/UID/geolocation state, online/match status, search/order controls and IP/UID ban actions.

`ClanSetupInterface` owns clan-name and rank/permission configuration.

`ClanWarsSetupInterface` preserves the exact title **Clan Wars Setup: Challenging xxxx** and the match-rule/arena selection surface.

`CollectionLogInterface` preserves the exact **Collection Log** title and its Bosses/Boxes/Minigames/Other categories, progress and completion rewards.

## Boundary

R291 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
