# Chat 2 — R4D semantic coverage projection

Exact v308 authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Chat 2 now provides a non-canonical coverage projection layer that overlays reviewed
semantic proposals as `CANDIDATE` on deep copies of canonical lineage and then reuses
core R4D `build_coverage_report()`.

It never writes `ACCEPTED` state and never mutates the supplied authority documents.

## Current semantic review

```text
review_id            SEMREVIEW_1D05C99BCABD6CB508EF
class proposals      58
field proposals       3
method proposals      4
total proposals      65
unresolved            0
```

## Exact-v308 baseline totals

The R1/R2C1 exact-v308 authority established:

```text
classes   1,129
fields    7,247
methods   6,564
entities 14,940
```

If the current 65 reviewed proposals are projected as `CANDIDATE` over the full v308
authority, expected candidate-known coverage is:

| Kind | Candidate | Total | Candidate-known % |
| --- | ---: | ---: | ---: |
| Classes | 58 | 1,129 | **5.1373%** |
| Fields | 3 | 7,247 | **0.0414%** |
| Methods | 4 | 6,564 | **0.0609%** |
| Overall | 65 | 14,940 | **0.4351%** |

Accepted/remap-ready semantic coverage remains **0%** until an explicit acceptance step
updates canonical lineage.

## Runtime projection contract

`project_semantic_review_coverage(...)`:

1. validates canonical class/member lineage;
2. binds the review to the exact build SHA;
3. refuses unresolved review sets;
4. refuses a proposal that conflicts with an existing `ACCEPTED` name;
5. overlays only `UNKNOWN -> CANDIDATE` on deep copies;
6. reuses the core R4D coverage report for base and projected states.

The actual repository integration test uses the committed 65-proposal review and verifies
that the projection contains exactly:

```text
classes candidate  58
fields candidate    3
methods candidate   4
overall candidate  65
overall accepted    0
```

This separates research progress from authorized readable-client coverage.
