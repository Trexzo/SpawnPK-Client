# Chat 2 — exact-v308 model recolor cycle R462

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

`rs/a/b/a$a` -> `CLIENT_CLASS_000060` -> `ModelRecolorCycle`

- proposal: `SEMPROP_9E8BA67EF757EB0B3141`
- review: `SEMREVIEW_2640768DC4017B8E5911`

## Exact role

R461 fixes the enclosing `rs/a/b/a` as `ModelRecolorOverride`.

Each inner object stores:

- one set of source face-color ids;
- one destination-color int array;
- one cursor.

The parent creates one inner object per configured recolor group and indexes it by the
source-color ids.

The inner object's only public operation returns the destination color at the current
cursor, increments the cursor and wraps to zero when it reaches the destination array
length.

The enclosing ModelRecolorOverride uses that returned value as the replacement written to
the matching Model face-color entry.

## Boundary

This is a deterministic per-group destination-color cycle. No animation, gameplay or
definition-domain behavior is claimed.

R462 remains non-canonical semantic research only.
