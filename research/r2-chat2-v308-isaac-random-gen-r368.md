# Chat 2 — exact-v308 ISAACRandomGen R368

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/q/a` -> `CLIENT_CLASS_000744` -> `ISAACRandomGen`
- proposal: `SEMPROP_C17BED4FC9B118DF5CBB`
- review: `SEMREVIEW_3BEAEDAD06F15D6E8F56`

## Exact algorithm fingerprint

The class owns:

- a 256-int result array;
- a 256-int internal memory array;
- result count;
- accumulator;
- last result;
- counter.

The generation round uses the canonical ISAAC xor/shift sequence:

- left 13;
- unsigned right 6;
- left 2;
- unsigned right 16.

Initialization seeds eight accumulators with `-1640531527` (`0x9e3779b9`) and performs
the standard repeated ISAAC mix before folding in the supplied seed array and producing the
first output block.

## Historical identity

Public 317 client sources preserve this exact class under the name `ISAACRandomGen`.
This is therefore an original legacy source identity, not a descriptive invention.

## Duplicate boundary

Adjacent `rs/cache/b` was explicitly rechecked and is already authoritative R64
`CacheStoreSet`; it is not duplicated here.

R368 remains non-canonical semantic research only.
