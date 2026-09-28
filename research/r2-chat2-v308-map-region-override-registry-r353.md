# Chat 2 — map region override registry R353

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/t/a/e` -> `CLIENT_CLASS_000987` -> `MapRegionOverrideRegistry`
- proposal: `SEMPROP_FA3CDE6560D002D4B8E5`
- review: `SEMREVIEW_BCE36959023682AC2011`

## Exact config authority

The class loads:

- `configs/maps.yaml`
- compiled fallback `configs/m.bin`

Recognized keys are exactly:

- `id`
- `map`
- `land`
- `type`
- `osid`
- `group`
- `forceroof` / `forceroofs`

## Cache/index mutation

The cache index loader constructs this registry and passes its live arrays for region ids,
map archive ids, land archive ids and region type. Configured values rewrite those arrays
in place.

The registry additionally retains exact lookup structures for:

- configured region id/group labels;
- configured region-id lookup;
- all configured map/land archive ids;
- OSRS-region membership;
- region-id -> OSRS-id remapping.

Region loading consults these tables before deriving world coordinates / archive behavior.

## Roof override

When a map config entry enables `forceroof` / `forceroofs`, the configured region id is
also inserted into the client's runtime region-override map.

## Boundary

This is client map/cache presentation and region-remap authority only. It does not imply
server-side world ownership or map collision authority.

R353 remains non-canonical semantic research only.
