# Chat 2 — exact-v308 region clip dump semantics R60

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R60 is a separate non-canonical class-only semantic review batch for the exact-v308
`::testregion` clip/map-position capture utility.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_F6010EA7F31DDA711385`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/e` -> `CLIENT_CLASS_000143`
- `rs/e$a` -> `CLIENT_CLASS_000144`

## `rs/e` -> `RegionClipDumper`

The privileged client command `::testregion` loads a requested region and then calls:

1. `rs/e.b()` to write the capture;
2. `rs/e.a()` to clear the saved map/position cache.

The class groups capture records by:

`(worldX >> 6) * 256 + (worldY >> 6)`

which is the standard 64x64 region-key composition. Positions are deduplicated by an
x/y/plane string key before insertion.

The class owns the hard-coded output root:

`./clipdump/`

and writes one binary file per captured region through `DataOutputStream`.

Surviving diagnostics include:

- `Cleared saved map and position cache!`
- `Dumping <n> regions..`
- `Dump successful!`

That fixes the role as a region collision/clip dump utility. The conservative semantic
name is `RegionClipDumper`.

## `rs/e$a` -> `RegionClipRecord`

This inner value object is constructed directly by RegionClipDumper and stores four
integer values plus one boolean corresponding to the captured world position / plane /
collision data and accompanying blocking metadata.

The dump writer iterates exactly these records and serializes the integer and boolean
state into the region file.

The conservative semantic name is `RegionClipRecord`.

## Naming boundary

These are semantic recovery names, not claims of verbatim original SpawnPK identifiers.

## Acceptance boundary

Chat 2 does not promote R60. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_F6010EA7F31DDA711385`.
