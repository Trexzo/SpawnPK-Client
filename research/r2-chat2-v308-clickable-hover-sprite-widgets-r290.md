# Chat 2 — exact-v308 clickable/hover sprite widgets R290

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/a/a` -> `CLIENT_CLASS_000526` -> `SpriteButtonWidget`
- `rs/n/a/b` -> `CLIENT_CLASS_000532` -> `HoverSpriteContainerWidget`
- review: `SEMREVIEW_B4E15495D4AC5E944EEC`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 behavior

`SpriteButtonWidget` is a type-5 sprite widget with interaction/action type 1 and an exact tooltip/action string. Live call sites use it for real clickable controls such as **Select tab**, **Search by item**, **Go back**, **Tips & Information**, **Teleport to Task**, **Claim rewards**, **Next chapter**, **Previous chapter** and **Select**.

Its hover attachment methods set the button's hover-interface id and build the paired secondary interface.

`HoverSpriteContainerWidget` is that secondary interface. It is a non-interactive one-child container whose dimensions come from the hover sprite, with the sprite inserted as child zero. Exact callers create normal/hover pairs such as wiki/button 1 -> 2, teleport sprite pairs, raids button pairs and bank button pairs.

Together with R289 this closes the typed `rs/n/a` widget-builder layer except package/root helpers.

## Boundary

R290 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
