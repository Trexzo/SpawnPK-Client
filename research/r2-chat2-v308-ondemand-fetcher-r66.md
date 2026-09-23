# Chat 2 — exact-v308 OnDemandFetcher semantics R66

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R66 is a separate non-canonical class-only semantic review batch in the cache/network
request lane. It is intentionally separate from R23's asset-updater family and R64's
CacheStoreSet.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_B32BB0529FC7A78DD9B4`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/cache/d` -> `CLIENT_CLASS_000097`

## `rs/cache/d` -> `OnDemandFetcher`

The exact-v308 class is an asynchronous cache/request engine.

It:

- implements `Runnable` and owns the long-lived worker loop;
- owns several Node/NodeSub-backed request queues;
- allocates `rs/cache/c` request records containing archive/type/id and delivery state;
- owns local cache stores for both SpawnPK and OSRS cache files;
- owns CRC/version tables plus a `CRC32` validator;
- validates fetched payloads against both version and CRC;
- owns socket, input-stream and output-stream state for remote retrieval;
- moves requests through pending, active and completed queues;
- exposes request/enqueue methods used by the client loading path.

The class is not the R23/R65 updater family. That family handles whole asset/update
coordination; this class services individual cache/on-demand requests and validates their
payloads.

This exact responsibility set is the classic client `OnDemandFetcher` architecture.
Exact v308 behavior is the primary authority; the historical name is corroborating
lineage evidence.

## R65 cleanup boundary

The formerly committed R65 updater batch was removed before R66 because it duplicated
R23 owners/names. R66 does not reuse any R23 owner and does not alter R23 evidence.

## Acceptance boundary

Chat 2 does not promote R66. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_B32BB0529FC7A78DD9B4`.
