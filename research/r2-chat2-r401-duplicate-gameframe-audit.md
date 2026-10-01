# Chat 2 — R401 duplicate gameframe audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R401 retains **no semantic proposal**.

The attempted proposals were both already owned:

- `rs/i/b` / `CLIENT_CLASS_000297`
  - existing R2 name: `AdventureOrbRenderer`
  - R2 proposal: `SEMPROP_A8CC480C3293E2CB6A8E`
- `rs/i/b$a` / `CLIENT_CLASS_000298`
  - existing R334 name: `GameframeSidebarTab`
  - R334 proposal: `SEMPROP_2954CFF2870D5050F667`

The global uniqueness guard correctly rejected the attempted R401 batch.

## Corroborating evidence

The newer exact-v308 inspection strengthens both earlier owners.

For `rs/i/b`, exact assets/behavior extend beyond the Adventure orb and show that the same
class owns broad gameframe/chrome rendering state: HP/prayer/run/spec orbs, chat controls,
sidebar icons, adventure/event/promo orbs, bank/equipment toggles and side-panel arrows.
This does not justify a second class identity; it is additional evidence for the existing R2
owner.

For `rs/i/b$a`, the exact enum constants remain:

`ATTACK, STATS, QUEST, INVENTORY, EQUIPMENT, PRAYER, MAGIC, CLAN, FRIENDS, IGNORE,
LOGOUT, OPTIONS, EMOTES, MUSIC`.

That directly corroborates R334 `GameframeSidebarTab`.

The sibling `rs/i/b$b` still contains only `TOP` and `BOTTOM`; the positioned noun is
not proven, so it remains intentionally unnamed.

## Boundary

R401 is a correction/corroboration note only. No candidate JSON, semantic-review JSON or
batch test remains.
