# Chat 2 — exact-v308 NodeSub Queue R103

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R103 is a separate non-canonical class-only review for the remaining classic secondary-link
queue primitive adjacent to R25 `Node` / `NodeSub` / `NodeList`.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_2E7F90192039A0BB2DE9`
- field/method proposals: **0**
- confidence: **0.999**

## Stable ID

- `rs/B` -> `CLIENT_CLASS_000027` -> `Queue`

## Exact-v308 contract

The class owns:

- one sentinel R25 `NodeSub`;
- one current-iteration `NodeSub`.

The constructor self-links the sentinel through the secondary NodeSub links.

Its mutating operations are the classic queue operations:

- insert one NodeSub at the sentinel head, unlinking it first when already linked;
- remove the tail NodeSub and unlink it before returning it.

Its iteration operations traverse the same secondary-link chain without mutation, and the
final integer method counts every linked NodeSub.

R24 `OnDemandFetcher` owns the exact queue and stores R24 `OnDemandData` nodes in it.
`OnDemandData` extends R25 `NodeSub`, independently fixing the element hierarchy.

## Historical-name corroboration

Classic 317/RSPS client source preserves a class literally named `Queue` with the same:

- sentinel NodeSub/Cacheable;
- current iteration node;
- `insertHead`;
- `popTail`;
- `reverseGetFirst`;
- `reverseGetNext`;
- `getNodeCount`.

This makes `Queue` a source-lineage-backed semantic identity rather than a descriptive
modern rename.

## Relationship to R25 / R52

R25 already recovered:

- `rs/t` -> `Node`;
- `rs/a` -> `NodeSub`;
- `rs/h` -> `NodeList`.

R52 recovered:

- `rs/o` -> `NodeHashTable`.

R103 closes the remaining classic secondary-link queue primitive used by the on-demand
request subsystem.

## Acceptance boundary

Chat 2 does not promote R103. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_2E7F90192039A0BB2DE9`.
