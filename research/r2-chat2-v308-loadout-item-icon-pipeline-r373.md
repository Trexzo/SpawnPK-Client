# Chat 2 — loadout item icon pipeline R373

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/b/g` -> `CLIENT_CLASS_000249` -> `LoadoutItemIconProvider`
- `rs/gui/b/b/b` -> `CLIENT_CLASS_000238` -> `LoadoutItemIconLoader`
- review: `SEMREVIEW_E9E2E74CF6E98F6724D6`

R144 already fixes `rs/gui/b/f` as `LoadoutItemEntry`. R345 fixes `rs/gui/x` as
`GuiImageAsset`.

The provider wraps one LoadoutItemEntry and maintains a shared icon cache keyed by item id.
On a miss it round-robins across five loader workers and returns null until the cache is
filled.

The loader resolves the 32x32 item sprite, removes black background pixels, wraps it in a
GuiImageAsset, inserts it into the shared cache and triggers the Launcher UI refresh path.

R373 remains non-canonical semantic research only.
