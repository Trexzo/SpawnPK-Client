# Chat 2 — exact-v308 model AABB implementation semantics R32

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R32 remains a separate non-canonical class-only semantic review batch. R222 corrects its
readable name after stronger upstream API evidence became available.

## Corrected deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- corrected review ID: `SEMREVIEW_FC24DE0B8A0F2CAF799C`
- corrected proposal ID: `SEMPROP_E4204F44044713ABAD56`
- field/method proposals: **0**

## `rs/a/i` -> `ModelAABB`

For a requested model angle, `Model.l(int)`:

1. rotates every model vertex into the requested orientation;
2. tracks exact minimum and maximum X, Y and Z;
3. computes three axis midpoints and three half-extents;
4. constructs `rs/a/i` with those six integers;
5. clamps X/Z half-extents to at least 32;
6. adds 8 units of X/Z padding when the model padding flag is set; and
7. caches the result by angle for render/picking use.

The target contains exactly six integer values, a six-argument constructor and six direct
getters. It implements `rs/runelite/a/a`.

## R222 correction

The original R32 proposal called this concrete object `AABB`:

- old proposal: `SEMPROP_0B9E8DFA9594EE5A8031`
- old review: `SEMREVIEW_F5DD2732F728A2946B02`

R222's upstream-source audit proves that `rs/runelite/a/a` itself corresponds to the
RuneLite API source interface `net.runelite.api.AABB`. Keeping the old R32 name would
therefore assign the one source-proven noun to the implementation and create a duplicate
when the interface is recovered.

The corrected descriptive implementation name is `ModelAABB`. It preserves the exact
model-bounds role without claiming an original implementation-class identifier.

## Acceptance boundary

Chat 2 does not promote corrected R32. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_FC24DE0B8A0F2CAF799C`.
