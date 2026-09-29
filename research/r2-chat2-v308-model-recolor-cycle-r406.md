# Chat 2 — model recolor cycle R406

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R399 already fixes the enclosing transform:

- `rs/a/b/a` -> `CLIENT_CLASS_000059` -> `ModelRecolorTransform`

R406 recovers its previously-unowned nested group/cycle state:

- `rs/a/b/a$a`
- `CLIENT_CLASS_000060`
- `ModelRecolorCycle`
- proposal `SEMPROP_9E8BA67EF757EB0B3141`
- review `SEMREVIEW_2640768DC4017B8E5911`

## Exact behavior

For every configured recolor group, ModelRecolorTransform constructs one nested instance.

That instance owns:

- the source-color id set for the group;
- the destination color int[] sequence;
- one cursor.

Its public value method returns the current destination color, advances the cursor, and
wraps to index zero at the end of the sequence.

The outer ModelRecolorTransform checks each model color/id against these source sets and
replaces a match with the group's next cyclic destination.

This directly closes the R399 evidence phrase “each configured recolor group owns a cyclic
destination int[] cursor.”

R406 remains non-canonical semantic research only.
