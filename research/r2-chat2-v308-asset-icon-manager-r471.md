# Chat 2 — exact-v308 AssetIconManager family R471

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/A/a` -> `CLIENT_CLASS_000002` -> `AssetIconManager`
- `rs/A/a$a` -> `CLIENT_CLASS_000003` -> `AssetIconManagerItemKey`
- `rs/A/a$b` -> `CLIENT_CLASS_000004` -> `AssetIconManagerSpriteKey`
- `rs/A/b` -> `CLIENT_CLASS_000005` -> `AssetIconItemCacheLoader`
- `rs/A/c` -> `CLIENT_CLASS_000006` -> `AssetIconSpriteCacheLoader`
- review: `SEMREVIEW_2CBAF57534518AA4337F`

## Preserved original identity

The two exact nested key classes leak their source identities in generated value-object
`toString()` constants:

`AssetIconManager.ItemKey(itemId=..., itemQuantity=..., size=...)`

and:

`AssetIconManager.SpriteKey(directory=..., size=...)`

That fixes the enclosing manager identity directly.

## Manager contract

The manager owns two Guava LoadingCaches:

- max size: 128
- expire after access: 1 hour
- value: R20 `AsyncBufferedImage`

The item cache key is exactly:

- itemId
- itemQuantity
- size

The sprite cache key is exactly:

- directory
- size

Item-icon generation resolves a game item sprite asynchronously and paints it into a
36x32 AsyncBufferedImage.

Named-sprite loading accepts resources such as `skills/1338`, loads the source Image and
either preserves intrinsic dimensions (size=-1) or uses the requested size.

The shared clear method invalidates and cleans up both caches and is used when info-box
presentation sizing changes.

## Loader boundary

The two adjacent Guava CacheLoader classes are synthetic delegating helpers. Their proposed
names are descriptive and scoped to the exact key/loader contract; no historical anonymous
class name is claimed.

R471 remains non-canonical semantic research only.
