# Chat 2 — R424 duplicate terrain-noise audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R424 retains **no semantic proposal**.

The R424 investigation independently recovered:

- `rs/p`;
- `CLIENT_CLASS_000739`;
- a procedural base-terrain height-noise role.

Its exact evidence confirms:

- plane-0 terrain height generation consumed by `rs/x`;
- three noise scales (4 / 2 / 1);
- deterministic coordinate hashing and smoothed/interpolated noise;
- final 10..60 clamp.

However, R104 already owns this exact class and stable ID:

- `rs/p` -> `CLIENT_CLASS_000739` -> `PerlinNoise`;
- proposal: `SEMPROP_664562B273117DBCA98E`;
- review: `SEMREVIEW_7E5DE83AA771BC1BB53C`.

R104 is also stronger naming authority because it records the same exact-v308 algorithm together
with matching historical/deobfuscated `PerlinNoise` identity and the classic ObjectManager
terrain-height consumer.

Therefore the former R424 `TerrainHeightNoise` candidate/review/test are removed. The R424
work is retained only as independent corroboration for R104 and as supporting context for
R425 ObjectManager.

R424 is a correction/audit batch only. Chat 2 performs no canonical acceptance or source rewrite.
