# Chat 2 — exact-v308 OSRS cache pack semantics R70

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R70 is a separate non-canonical class-only semantic review batch for the exact-v308
OSRS asset-pack/cache-index import path.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_E717D253AD955D38DC5D`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/cache/osrs/a` -> `CLIENT_CLASS_000099`
- `rs/cache/osrs/b` -> `CLIENT_CLASS_000100`

## `rs/cache/osrs/a` -> `OsrsCacheIndex`

This exact enum has four surviving constant names:

- `MODELS`
- `ANIMS`
- `SOUNDS`
- `MAPS`

Each value owns a numeric cache-store index and a human label. Its constructor also derives
an exact `osrs_idx<id>` path from the R66 `Signlink` cache-directory root.

R70's second class consumes all three pieces directly: path for the pack directory, label
for diagnostics, and numeric index for selecting a Decompressor from R64 `CacheStoreSet`.

That is a strong exact-v308 identity for an OSRS cache-index/category enum.

## `rs/cache/osrs/b` -> `OsrsAssetPacker`

This class is constructed by R24 `OnDemandFetcher` after the OSRS cache files
`main_file_osrs.dat` / `main_file_osrs.idx` are initialized. When the exact feature flag is
enabled, OnDemandFetcher immediately invokes this object's pack operation.

The packer iterates every `OsrsCacheIndex`, opens the corresponding pack directory, and
examines its files. Exact surviving diagnostics include:

- `Scanning assets in pack directory {} index (file count: {})`
- `Packed new assets into {} index ({} files)`
- `Unable to locate index {}.`

Only `.gz` asset files are considered. The filename-derived numeric asset id is parsed,
the file bytes are read, and those bytes are written into the R64 `CacheStoreSet`
Decompressor selected by the enum's numeric index.

That exact scan/read/write contract fixes the role as `OsrsAssetPacker`.

## Naming boundary

Both names are semantic recovery names. R70 does not claim they are verbatim original
SpawnPK developer identifiers.

## Acceptance boundary

Chat 2 does not promote R70. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_E717D253AD955D38DC5D`.
