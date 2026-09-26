# Chat 2 — exact-v308 ModelHeader semantics R36

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R36 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R35 candidate batches.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_AD69F191733BF4798072`
- field/method proposals: **0**

## `rs/v` -> `ModelHeader`

The role is fixed by both the exact producer and the exact Model consumer.

### Producer

`Model.a(byte[], int, boolean)` reads the trailer/footer of one model payload using R29
`Stream`, allocates an `rs/v` record for the model id, and stores:

- the original model `byte[]`;
- three leading counts; and
- a sequence of calculated offsets into the payload.

Conditional sections are represented either by their computed offset or by a negative
sentinel when absent.

### Count binding

When a `Model` instance is built from the registered model id, it reads that `rs/v`
record first. The first three integers are copied into the Model state that drives the
vertex, triangle/face and textured-triangle data structures.

The model workspace is then sized using those counts before decoding begins.

### Section-offset binding

The remaining `rs/v` fields are consumed as byte offsets. Model creates multiple R29
`Stream` views over the same payload and moves each view to one of those offsets so each
encoded section can be decoded independently.

Therefore `rs/v` is not a model object itself. It is the compact metadata/header record
that describes how to decode one model payload.

`ModelHeader` is the conservative semantic name for that role.

## Acceptance boundary

Chat 2 does not promote R36. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to
`SEMREVIEW_AD69F191733BF4798072`.
