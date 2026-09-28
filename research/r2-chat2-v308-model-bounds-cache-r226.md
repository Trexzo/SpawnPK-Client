# Chat 2 — exact-v308 RSInterface model-bounds cache entry R226

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R226 reviews the final substantive unreviewed class in `rs/runelite/a/*`.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_FBA59B2AA1F0C2CF6DA0`
- field/method proposals: **0**

## Stable ID

- `rs/runelite/a/d` -> `CLIENT_CLASS_000812` -> `ModelBoundsCacheEntry`

## Exact structure

The class:

- extends the client's linked-list `Node` base;
- owns exactly eight integer values;
- has only its default constructor;
- is referenced outside itself only by recovered `RSInterface`.

That shape is explained completely by its one live consumer.

## Exact save/restore flow

Inside the RSInterface model-building path, the exact client optionally enables a model-bounds
cache for the interface model ID.

On a miss:

1. the Model bounds calculation `Model.m()` runs;
2. RSInterface allocates `rs/runelite/a/d`;
3. it copies eight Model bounds values into the entry;
4. it inserts the Node-backed entry into an `rs/F` cache keyed by the interface model ID.

The eight stored values are the exact Model min/max X and Z extents, model height, bottom Y,
radius and diameter values produced by the bounds scan.

On a hit, RSInterface copies the same eight integers back into the prepared Model before
returning it, avoiding the full bounds recomputation.

## Naming boundary

`ModelBoundsCacheEntry` is descriptive exact-behavior recovery at confidence **0.998**.
The evidence proves a model-bounds snapshot/cache record, but not an original source-level
class identifier.

## Acceptance boundary

Chat 2 does not promote R226. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_FBA59B2AA1F0C2CF6DA0`.
