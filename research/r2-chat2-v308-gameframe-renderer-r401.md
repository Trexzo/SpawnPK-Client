# Chat 2 — exact-v308 gameframe renderer R401

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/i/b` -> `CLIENT_CLASS_000297` -> `GameFrameRenderer`
- `rs/i/b$a` -> `CLIENT_CLASS_000298` -> `SidebarTab`
- review: `SEMREVIEW_575136AEDEBDC81967B2`

## GameFrameRenderer

The exact class owns the client chrome/gameframe presentation assets and render state.

Surviving asset families include:

- HP / prayer / run / special-attack orb fill + icon sprites;
- active/hover orb states;
- gameframe chat buttons and redstones;
- sidebar icons;
- adventure, event and promo orbs;
- bank inventory/equipment toggles;
- heal/refill/boss/XP/hit toggles;
- left/right side-panel arrows.

Client retains one instance and invokes it from central rendering/layout paths.

## SidebarTab

The nested enum preserves fourteen exact names:

`ATTACK, STATS, QUEST, INVENTORY, EQUIPMENT, PRAYER, MAGIC, CLAN, FRIENDS, IGNORE,
LOGOUT, OPTIONS, EMOTES, MUSIC`.

Each entry stores its tab index plus render/layout metadata, and the enum supports lookup by
tab index.

## Withheld nested enum

`rs/i/b$b` contains only `TOP` and `BOTTOM`.

Those values prove a two-position concept but not the noun being positioned, so the class
remains intentionally unnamed.

## Boundary

The outer name is descriptive exact-v308 behavior, not a claim that `GameFrameRenderer`
was the original stripped developer identifier.

R401 remains non-canonical semantic research only.
