# Chat 2 — exact-v308 text-particle selection timestamp cache R419

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/u` -> `CLIENT_CLASS_000512` -> `TextParticleSelectionTimestampCache`
- proposal: `SEMPROP_E39EC688F0077EE46607`
- review: `SEMREVIEW_9D0438B218AE4011D119`

## Exact role

R362 `TextParticleMarkup` is the only exact-v308 owner.

The cache is an access-ordered `LinkedHashMap<Long,Long>` with:

- initial capacity 64;
- load factor 0.75;
- eldest eviction above 512 entries.

TextParticleMarkup derives the key from the source String hash plus markup span indexes and
stores the current monotonic millisecond timestamp.

If the same span key was selected less than **50 ms** earlier, TextParticleMarkup reuses the
existing particle variant selection instead of choosing another random palette/image set.

## Boundary

This cache does not own particle rendering or motion. It only stabilizes the selection
timestamp window used by TextParticleMarkup.

R419 remains non-canonical semantic research only.
