# Chat 2 — exact-v308 on-demand cache semantics R24

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R24 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R23 review batches.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_1FA45238A375A306F3C7`
- field/method proposals: **0**

## On-demand cache family

- `rs/cache/c` -> `OnDemandData`
- `rs/cache/d` -> `OnDemandFetcher`
- `rs/cache/e` -> `OnDemandFetcherParent`

### OnDemandData

Exact SpawnPK v308 structure stores the request's data type/id, received byte buffer,
incomplete/priority state, retry loop counter and adjacent request metadata. OnDemandFetcher
queues these nodes, matches incoming type/id headers, fills their buffers and moves completed
requests between queues.

Classic 317-source cross-checks expose the structurally identical node as
`OnDemandData` with the same `dataType`, `ID`, `buffer`, `incomplete` and
`loopCycle` roles.

### OnDemandFetcher

Exact SpawnPK v308:

- extends `rs/cache/e`;
- implements Runnable;
- owns request queues, CRC32 state, socket/input/output streams and cache/version arrays;
- validates CRC + trailing version values;
- queues and retries incomplete requests;
- reads the six-byte response header and paged response payload;
- writes completed files to the local cache;
- resets stalled network state after retry/loop thresholds;
- contains the surviving `od_ex ` error prefix.

The classic OnDemandFetcher implementation matches this same Runnable/superclass/queue/socket
algorithm and OnDemandData interaction nearly line-for-line.

### OnDemandFetcherParent

Exact SpawnPK v308 is the minimal parent request abstraction extended by OnDemandFetcher.
Model/cache consumers retain the parent type and invoke its integer request hook when an
asset/model is missing.

Classic client source independently exposes the corresponding parent type as
`OnDemandFetcherParent`.

## Evidence boundary

Historical 317 client source is used only to corroborate the inherited class identities.
The semantic authority for this batch remains the pinned SpawnPK v308 implementation.

Generic node/deque/cache-sector classes used internally by the fetcher are deliberately not
named by R24.

## Acceptance boundary

Chat 2 does not promote R24. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_1FA45238A375A306F3C7`.
