# Chat 2 — candidate semantic carry-forward projection

R4E correctly handles only canonical `ACCEPTED` semantics.

Chat 2 now adds a lower-authority research projection for semantic review sets that have not
been accepted yet.

## Purpose

For one old-build `semantic_review_set`, determine whether each reviewed stable class,
field or method ID has a canonical identity relation in a newer build.

This answers:

> If this proposal were later accepted, does the same logical entity still exist in the
> new build?

It does **not** answer whether the semantic name should be accepted.

## Classification

Each reviewed proposal is classified as:

- `carried` — the stable ID has both old and new build lineage;
- `blocked_missing_new_identity` — the reviewed old-build entity has no new-build
  identity relation.

Unlike R4E, there is no `available_new_only` bucket because a review set originates from
the old build and therefore contains no new-only semantic proposal by definition.

## Safety

`project_candidate_carryforward(...)`:

- validates canonical class/member lineage;
- binds the review SHA to the old exact build;
- requires the new build to exist in canonical lineage;
- refuses unresolved semantic reviews;
- refuses unknown stable IDs and member-kind mismatches;
- does not mutate class or member lineage;
- does not write `CANDIDATE` or `ACCEPTED` state;
- does not invoke R4E readable-build readiness.

R4E remains the sole canonical accepted-name carry-forward path.

## Current exact-v308 semantic review

Current Chat 2 review:

```text
review_id            SEMREVIEW_1D05C99BCABD6CB508EF
class proposals      58
field proposals       3
method proposals      4
total proposals      65
unresolved            0
```

There is no promoted post-v308 authority in this repository conversation yet, so no real
future-build carry-forward result is claimed here. The projector is ready for the next
exact client update once R3 has established the new canonical identity relations.
