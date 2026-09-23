# Chat 2 — exact-v308 StreamPool semantics R35

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R35 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R34 candidate batches.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_EE8EC3AFB80B5F24AF1B`
- field/method proposals: **0**

## `rs/a/a/c` -> `StreamPool`

R29 already identifies `rs/x/e` as the classic client `Stream`.

`rs/a/a/c` contains:

- a static array of exactly ten `rs/x/e` objects;
- a shared cursor into that array;
- `a(byte[])`, which returns the current slot;
- lazy creation via `new Stream(byte[])` when the slot is empty;
- reuse via rebinding an existing Stream to the supplied byte array; and
- a reset method that clears pooled backing-array references and rewinds the cursor.

The key consumer is exact-v308 `Model` decoding. Before decoding a model payload the
client resets this class, then repeatedly requests several Stream instances over the same
model byte array and moves each Stream to a different section offset.

That makes the class a temporary reusable **Stream pool**, not a model definition or
archive object. `StreamPool` is therefore the conservative semantic name.

## Acceptance boundary

Chat 2 does not promote R35. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to
`SEMREVIEW_EE8EC3AFB80B5F24AF1B`.
