# Chat 2 successor — exact-v308 mystery-container reward preview R372

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/r` -> `CLIENT_CLASS_000771` -> `MysteryContainerRewardPreview`
- proposal: `SEMPROP_29641FC19888F4BBA4F0`
- review: `SEMREVIEW_BC80F4BED06E9C7AE483`

## Exact role

`rs/r` has no fields and one meaningful static method:

`boolean a(String itemName)`

It recognizes many exact reward-container names including Donator mystery box, Blood key /
Grand blood key, PvP mystery box, Bond casket / Bond casket key, and seasonal
Easter/H'ween/Summer/Winter caskets/packages.

For each recognized name it builds rich multiline description text plus an `int[]` of
representative reward item IDs. Unrecognized names return `false`.

## Exact tooltip join

On a recognized container the class derives placement from current mouse coordinates and
calls `Client.a(int,int,String,int[])`.

That Client method constructs R207 `TooltipContent`, attaches the reward item IDs and
submits it to R207 `TooltipOverlay`.

## Boundary

The class does not open containers, choose rewards, mutate inventory or prove server reward
tables. Its arrays/text are client presentation authority only.

R372 remains non-canonical semantic research only.
