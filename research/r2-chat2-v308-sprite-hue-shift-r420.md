# Chat 2 — exact-v308 sprite hue shift R420

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/L` -> `CLIENT_CLASS_000361` -> `SpriteHueShift`
- proposal: `SEMPROP_9752E964073A70D7B67D`
- review: `SEMREVIEW_063F45CEF7DC9A115644`

## Exact role

R361 `SpriteStyleTransformer` is the only live exact-v308 consumer.

The transform:

1. decomposes RGB into min/max/delta state;
2. derives a hue-sector coordinate over 0..1535;
3. rotates hue by `shift * 6` modulo 1536;
4. converts the rotated hue back to RGB;
5. optionally blends the transformed RGB against the original by a clamped 0..100% amount.

The two-argument helper applies the same hue shift at 100% transformed color.

SpriteStyleTransformer invokes this helper for nontransparent inline-sprite pixels when a
style color transform is active. Size adjustment and vertical gradient/phase behavior remain
owned by SpriteStyleTransformer.

## Boundary

`SpriteHueShift` is descriptive exact-v308 behavioral recovery. No original source class
identifier is claimed.

R420 remains non-canonical semantic research only.
