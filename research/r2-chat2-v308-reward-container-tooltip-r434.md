# Chat 2 — exact-v308 reward-container tooltip resolver R434

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/r` -> `CLIENT_CLASS_000771` -> `RewardContainerTooltipResolver`
- proposal: `SEMPROP_77FDBAE752FF8E5D392C`
- review: `SEMREVIEW_C015FA9C259CB75645A6`

## Exact presentation catalogue

The class exposes one large String resolver. It recognizes exact container/package names such as:

- Donator mystery box
- PvP mystery box
- Exotic mystery box
- Blood key / Grand blood key
- Bond casket / Bond casket key
- Rare event box
- Mystery crate
- seasonal/event caskets and packages
- multiple bond/package variants

Each recognized branch builds an int[] of representative item-definition IDs and may rewrite
the displayed tooltip label.

## Exact tooltip join

When a branch resolves, the class calls:

`Client.a(x, y, label, itemIds)`

The exact Client implementation:

1. constructs R207 `TooltipContent`;
2. stores the int[] item IDs on that content;
3. submits the content to R207 `TooltipOverlay`.

The boolean return simply reports whether a preview branch was recognized.

## Critical authority boundary

This class does **not** roll rewards, mutate inventory, choose quantities, or send a server
request. Its hardcoded arrays are presentation previews only.

They must not be promoted into authoritative server reward tables or probability definitions.

R434 remains non-canonical semantic research only.
