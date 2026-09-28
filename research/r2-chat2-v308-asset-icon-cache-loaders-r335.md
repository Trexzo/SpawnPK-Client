# Chat 2 — exact-v308 AssetIcon cache loaders R335

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/A/b` -> `CLIENT_CLASS_000005` -> `AssetIconItemCacheLoader`
- `rs/A/c` -> `CLIENT_CLASS_000006` -> `AssetIconSpriteCacheLoader`
- review: `SEMREVIEW_6E97CC5F38F394054F04`

R19 already recovers the enclosing `AssetIconManager`, its two exact key types and the
`AsyncBufferedImage` value type.

The manager constructs two independent expiring caches:

1. `AssetIconItemKey -> AsyncBufferedImage`, loaded by `rs/A/b`;
2. `AssetIconSpriteKey -> AsyncBufferedImage`, loaded by `rs/A/c`.

The item loader extracts item id, quantity and size and delegates to the manager's item-image
creation path.

The sprite loader extracts sprite directory and size and delegates to the manager's sprite-image
creation path.

These are exact typed cache-loader roles, not inferred generic helpers.

R335 remains non-canonical semantic research only.
