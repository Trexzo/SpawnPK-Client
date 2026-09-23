# Chat 2 — exact-v308 model AABB semantics R32

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R32 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R31 review batches.

The branch first integrated Main R8E and restored the required post-R8E gate:

- Chat 2 reconciliation head before R32: `063c024734523c1dd955323b77271172afe24250`
- behind Main: **0**
- merge base: R8E `f6ec242e607e6c7d6d98dd5b2421d38568d67946`
- Recovery CI run: `35805526464`
- Ubuntu: **success**
- Windows: **success**

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_F5DD2732F728A2946B02`
- field/method proposals: **0**

## `rs/a/i` -> `AABB`

R31 deliberately left `rs/a/i` unnamed. R32 resolves it only after following its exact
construction path inside R30 `Model`.

For a requested model angle, `Model.l(int)`:

1. rotates every model vertex into the requested orientation;
2. tracks exact minimum and maximum X, Y and Z coordinates;
3. computes the midpoint of each axis;
4. computes one half-extent for each axis;
5. constructs `rs/a/i` with exactly those six integers;
6. clamps the X/Z half-extents to at least 32;
7. adds a further 8 units of X/Z padding when the model padding flag is set; and
8. caches the resulting object by angle for later render/picking use.

The target class itself contains exactly six integer values, a six-argument constructor,
and six direct getters. It implements the matching six-coordinate
`rs.runelite.a.a` interface and carries no unrelated state.

That combination fixes the role as an axis-aligned bounding box value object. The proposed
semantic name is therefore `AABB`.

This is a semantic recovery name, not a claim that the original developer identifier has
been recovered verbatim.

## Adjacent classes still withheld

R32 intentionally does **not** force names onto the other classes that R31 left open:

- `rs/a/d` is a compact triple-array geometry accumulator used by model processing, but
  the exact semantic noun remains underdetermined.
- `rs/a/e` owns four active `rs/a/f` slots plus an overflow/replay list and is bound to
  every Actor.
- `rs/a/f` stores one damage-display record and contains the sprite/number rendering
  paths used by the client.

The `rs/a/e` / `rs/a/f` behavior is clearly hit-display related, but the exact semantic
choice between terms such as hitmark, hitsplat, damage marker, and manager/record is not
yet uniquely anchored by surviving v308 evidence. They remain unnamed rather than lowering
the naming standard.

## Acceptance boundary

Chat 2 does not promote R32. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to
`SEMREVIEW_F5DD2732F728A2946B02`.
