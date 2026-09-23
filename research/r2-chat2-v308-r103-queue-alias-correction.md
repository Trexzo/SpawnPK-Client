# Chat 2 — R103 redundant Queue alias correction

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

A temporary R103 semantic review attempted to propose:

- `rs/B` -> `Queue`

The review itself resolved deterministically, but its non-overlap test correctly failed on
both CI platforms because `rs/B` was already reviewed in R47 as:

- `rs/B` -> `CLIENT_CLASS_000027` -> `NodeSubList`
- proposal `SEMPROP_BC35BFB99246D3641A68`
- review `SEMREVIEW_9BF3AD4F6D29C99D0FD8`

R47 also already reviews the adjacent cache wrapper:

- `rs/F` -> `CLIENT_CLASS_000033` -> `MruNodeCache`

so no follow-up `MRUNodes` proposal should be created either.

## New evidence retained

The exact-v308 behavior remains unchanged:

- `rs/B` owns a circular sentinel R25 `NodeSub`;
- insertion promotes at the head;
- removal pops/unlinks the tail;
- reverse iteration and node counting use the same secondary link pair;
- R24 `OnDemandFetcher` consumes it with `OnDemandData extends NodeSub`.

Additional public 317-era source inspection found an equivalent class literally named
`Queue`, with the same:

- `insertHead`;
- `popTail`;
- `reverseGetFirst`;
- `reverseGetNext`;
- `getNodeCount`.

Other classic client lineages use the name `NodeSubList` for the same structure.

Likewise, public classic source preserves `MRUNodes` for the exact algorithm already
covered by R47 `MruNodeCache`: fixed capacity, NodeHashTable lookup, recency-list
promotion, tail eviction, sentinel skip and full unlink/reset.

## Resolution

R103 is intentionally left with **no committed semantic review**.

The temporary candidate/review/test/research files were removed after CI exposed the owner
collision. This note preserves the useful historical-name evidence without creating a
second proposal for either R47 owner.

No canonical authority is changed.
