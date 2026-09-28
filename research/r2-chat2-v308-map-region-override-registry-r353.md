# Chat 2 — R353 duplicate map-region audit

R353 retains **no semantic proposal**.

Direct exact-v308 inspection rediscovered `rs/t/a/e`, already owned by **R81**.

New corroborating evidence:

- loads `configs/maps.yaml` / `configs/m.bin`;
- parses `id/map/land/type/osid/group/forceroof(s)`;
- rewrites live region/map/land/type cache-index arrays;
- owns configured region/archive/group/OSRS-remap lookup structures;
- region loading consults the remap state;
- forced-roof config feeds the client runtime region-override map.

The attempted R353 candidate/review/test artifacts are removed. This is a zero-retained
corroboration batch only.
