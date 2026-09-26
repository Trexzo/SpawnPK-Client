# Chat 2 — exact-v308 cache store set semantics R64

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R64 is a separate non-canonical class-only semantic review batch adjacent to the already
recovered R24 on-demand update subsystem and R25 Decompressor cache store.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_92D4CB62913C3F67FCF8`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/cache/b` -> `CLIENT_CLASS_000095`

R25 already recovers:

- `rs/cache/a` -> `Decompressor`

R24 already recovers:

- `rs/cache/c` -> `OnDemandData`
- `rs/cache/d` -> `OnDemandFetcher`
- `rs/cache/e` -> `OnDemandFetcherParent`

## `rs/cache/b` -> `CacheStoreSet`

The class owns:

- one shared data `RandomAccessFile`;
- exactly five index `RandomAccessFile` objects;
- exactly five `Decompressor` instances.

Its initializer accepts a data filename and an index-prefix string. It opens the data file,
opens five index files using suffixes 0 through 4, then constructs five Decompressor
instances with store ids 1 through 5 over the shared data file and corresponding index.

The only public getter returns that five-element `Decompressor[]`.

R24 `OnDemandFetcher` owns four of these sets. It initializes them with the exact names:

- `main_file_cache.dat` / `main_file_cache.idx`
- `main_file_osrs.dat` / `main_file_osrs.idx`

Consumers then select a specific Decompressor from the returned store array.

That fixes the class as a grouped cache-store set rather than an individual cache store or
the update manager itself. The conservative semantic name is `CacheStoreSet`.

## Naming boundary

This is a semantic recovery name and does not claim a verbatim original SpawnPK identifier.

## Acceptance boundary

Chat 2 does not promote R64. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_92D4CB62913C3F67FCF8`.
