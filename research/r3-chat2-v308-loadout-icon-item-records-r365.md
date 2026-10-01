# Chat 2 R3 — Loadouts icon/item records R365

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/b/e` -> `CLIENT_CLASS_000247` -> `LoadoutIcon`
- `rs/gui/b/f` -> `CLIENT_CLASS_000248` -> `LoadoutItemEntry`
- `rs/gui/b/g` -> `CLIENT_CLASS_000249` -> `LoadoutItemIconCache`
- review: `SEMREVIEW_E8DBE2182C0685BA9F6B`

`LoadoutIcon` is the 29-value icon/category enum already serialized by the promoted
LoadoutBinaryCodec.

`LoadoutItemEntry` is the exact two-int itemId/quantity record used in both equipment and
inventory slots. Quantity rendering is independently visible in the Loadouts renderer.

`LoadoutItemIconCache` maps item IDs to 32x32 GuiImageAsset images and dispatches an async
miss path through the loadout icon-loader helpers.

The odd `rs/gui/b/b/b` helper is not named here because its Runnable entry point is empty;
its useful behavior is reached indirectly through callback registration and does not need a
forced standalone semantic identity.

R365 remains non-canonical semantic research only.
