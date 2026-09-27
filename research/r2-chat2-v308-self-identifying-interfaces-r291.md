# Chat 2 — exact-v308 duel preset load interface R291

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/D` -> `CLIENT_CLASS_000549` -> `DuelPresetLoadInterface`
- review: `SEMREVIEW_9015A3B42909159C7E85`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 evidence

The class preserves the exact actions **Load last duel** and **Load last rules** and loads the exact `misc/duel load` resource. That fixes the class as the duel preset/rules reload interface.

## Prior authority retained

The first draft of R291 also revisited five interfaces that already had R2 authority. They are intentionally not re-proposed:

- `rs/n/c/G` -> `ItemEnchantmentInterface`
- `rs/n/c/U` -> `PlayerIpUidMatcherInterface`
- `rs/n/c/p` -> `ClanChatSetupInterface`
- `rs/n/c/s` -> `ClanWarsSetupInterface`
- `rs/n/c/v` -> `CollectionLogInterface`

## Boundary

R291 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
