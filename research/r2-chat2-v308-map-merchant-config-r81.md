# Chat 2 — exact-v308 map / wandering-merchant config loaders R81

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R81 is a separate non-canonical class-only semantic review batch for the two remaining
strongly self-identifying `rs/t/a/*` config classes deliberately withheld from R80.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_B8D25FA5E0542C9A9585`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/t/a/e` -> `CLIENT_CLASS_000987`
- `rs/t/a/g` -> `CLIENT_CLASS_000989`

## `rs/t/a/e` -> `MapConfigLoader`

Exact sources:

- `configs/maps.yaml`
- `configs/m.bin`

This class extends the same R80 file/config support base but has a map-specific aggregate
schema rather than producing one R28 definition object per id.

Its exact keys are:

- `id`
- `map`
- `land`
- `type`
- `osid`
- `group`
- `forceroof`
- `forceroofs`

The decoder writes directly into the four map-index arrays supplied by R24
`OnDemandFetcher`, while also building lookup/set metadata for map ids, map/land archives,
OSRS entries, grouping and forced-roof handling.

R24 OnDemandFetcher constructs this class during its map/cache-index initialization and
passes those arrays into the loader. Exact Client consumers then use the resulting metadata
to compare configured region groups, select map archives and switch OSRS map handling.

That direct source identity + schema + OnDemandFetcher/Client data flow supports the
conservative `MapConfigLoader` role without claiming an original identifier.

## `rs/t/a/g` -> `WanderingMerchantItemConfigLoader`

Exact sources:

- `configs/wandering_merchant.yaml`
- `configs/w.bin`

The loader walks top-level sections, reads the exact nested key `items`, extracts each
entry's integer `id`, performs a narrow ItemDefinition normalization, and inserts the
resulting ids into a static integer set.

The Client constructs and loads this class directly during startup.

The loaded set has an exact presentation consumer: item-hover rendering checks whether the
current item id belongs to the set and, when the corresponding tooltip option is enabled,
appends:

` <img=370>`

to the rendered item text.

The exact file identity, item schema, startup wiring and render consumer together fix the
semantic role strongly enough for `WanderingMerchantItemConfigLoader`.

## Naming boundary

Both names are conservative semantic recovery names. R81 does **not** claim either is a
verbatim original SpawnPK developer identifier.

## Acceptance boundary

Chat 2 does not promote R81. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_B8D25FA5E0542C9A9585`.
