# R2 Chat 2 — canonical R2C2 semantic-review validation

Date: 2026-09-22

Exact v308 authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

This validation re-ran Chat 2's semantic coordinates against the canonical R1/R2C1
deterministic identity rules and then through the R2C2 semantic-review contract.

## Important correction

Earlier Chat 2 hand-written notes contained a few off-by-one/off-by-two class IDs.
Those temporary IDs have been replaced by coordinates re-derived from the immutable v308
baseline ordering and verified through R2C2.

Examples:

- `rs/Client` -> `CLIENT_CLASS_000029`
- `rs/i/b` -> `CLIENT_CLASS_000297`
- `rs/n/c/G` -> `CLIENT_CLASS_000552`
- `rs/n/c/aL` -> `CLIENT_CLASS_000587`
- `rs/n/c/am` -> `CLIENT_CLASS_000614`
- `rs/n/c/av` -> `CLIENT_CLASS_000626`
- `rs/n/c/b` -> `CLIENT_CLASS_000632`
- `rs/n/c/c` -> `CLIENT_CLASS_000640`
- `rs/n/c/v` -> `CLIENT_CLASS_000675`
- `rs/n/c/z` -> `CLIENT_CLASS_000679`

The old parallel remap-proposal bridge has been removed from the Chat 2 branch. R2C2 now
owns coordinate resolution.

## Exact member IDs

The R2C1 baseline seed over v308 contains:

- 7,247 canonical fields
- 6,564 canonical non-constructor methods

The seven Chat 2 member candidates resolve to:

| Raw coordinate | Stable R2C1 ID | Candidate |
| --- | --- | --- |
| `rs/Client.P:I` | `CLIENT_FIELD_000156` | `loginRewardContainerIndex` |
| `rs/Client.a(J)V` | `CLIENT_METHOD_000298` | `addFriend` |
| `rs/Client.f(J)V` | `CLIENT_METHOD_000473` | `removeFriend` |
| `rs/Client.h(J)V` | `CLIENT_METHOD_000491` | `addIgnore` |
| `rs/Client.i(J)V` | `CLIENT_METHOD_000498` | `removeIgnore` |
| `rs/i/b.f:Lrs/l/F;` | `CLIENT_FIELD_002923` | `adventureOrbSprite` |
| `rs/i/b.g:Lrs/l/F;` | `CLIENT_FIELD_002924` | `adventureOrbHoverSprite` |

## R2C2 semantic resolve

Input:

`mappings/candidates/v308.semantic.chat2.r2.json`

Canonical R2C2 output:

`mappings/candidates/v308.semantic-review.chat2.r2.json`

Current result:

```text
candidates   45
proposals    45
unresolved   0
review_id    SEMREVIEW_E471CA15CA95C7CD00A7
```

The review contains:

- 38 class proposals
- 3 field proposals
- 4 method proposals

A repository integration test executes the committed candidate set through
`resolve_semantic_candidates()` and requires object-for-object equality with the committed
review output, including the deterministic review ID.

## Trust boundary

This document does not select any `SEMPROP_*` identifier for acceptance.

R2C2 requires a separate `semantic_acceptance_spec` naming the exact review ID and exact
proposal IDs selected by the user/project. Chat 2 therefore stops at a verified,
non-canonical `semantic_review_set` until that explicit selection exists.
