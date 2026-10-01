# Chat 2 — sprite color helper and text-particle timestamp cache R391

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/L` -> `CLIENT_CLASS_000361` -> `SpriteColorAdjustmentUtil`
- `rs/l/u` -> `CLIENT_CLASS_000512` -> `TextParticleTimestampCache`
- review: `SEMREVIEW_B0F5AF704F4B7BD3D075`

## SpriteColorAdjustmentUtil

Exact-v308 reference scanning finds `rs/l/L` used only by R361
`SpriteStyleTransformer`.

Its static methods:

- normalize a style/color parameter to the 1..255 domain;
- clamp a percentage to 0..100;
- adjust packed color hue bits;
- transform RGB hue/strength/percentage values.

`SpriteStyleTransformer` applies the result while rewriting Sprite pixels and preserves
alpha separately around the transformed RGB component.

The proposed name therefore stays at utility scope and does not invent a narrower original
class noun.

## TextParticleTimestampCache

`rs/l/u` extends access-order `LinkedHashMap<Long, Long>`.

It evicts the eldest entry once size exceeds exactly **512**.

R362 `TextParticleMarkup` is its only live external owner. The markup code:

1. hashes String + two integer parameters into a long key;
2. reads current milliseconds from `System.nanoTime()/1_000_000`;
3. checks the stored timestamp;
4. skips regeneration while the same key is younger than **50 ms**;
5. otherwise stores the new timestamp.

The class is therefore a bounded timestamp cache for text-particle generation.

R391 remains non-canonical semantic research only.
