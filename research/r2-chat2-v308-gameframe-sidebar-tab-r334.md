# Chat 2 — exact-v308 gameframe sidebar tab enum R334

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/i/b$a` -> `CLIENT_CLASS_000298` -> `GameframeSidebarTab`
- proposal: `SEMPROP_2954CFF2870D5050F667`
- review: `SEMREVIEW_F3237D35F41211170652`

## Exact constants

The enum preserves the complete 14-value classic sidebar/tab set:

- ATTACK
- STATS
- QUEST
- INVENTORY
- EQUIPMENT
- PRAYER
- MAGIC
- CLAN
- FRIENDS
- IGNORE
- LOGOUT
- OPTIONS
- EMOTES
- MUSIC

Each value carries a primary integer 0..13 and additional presentation/index metadata.
The static integer lookup returns the tab with the matching primary id.

## Parent join

The enum is nested inside `rs/i/b`, reviewed in R2 as the gameframe/adventure-orb
renderer. R164 independently proves the same owner renders gameframe chat-channel controls
and consumes `ChatMessageClassifier`.

The enum constants therefore fix a sidebar/gameframe tab identity rather than a generic
mode enum.

## Withheld sibling

`rs/i/b$b` contains only TOP/BOTTOM. Exact class references do not show a behavioral
consumer beyond the enclosing-class metadata, so R334 does not invent a row/placement noun
for it.

R334 remains non-canonical semantic research only.
