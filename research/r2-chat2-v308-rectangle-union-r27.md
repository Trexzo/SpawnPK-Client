# Chat 2 — exact-v308 rectangle union semantics R27

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R27 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R26 review batches.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_95A9F1C60A382FDF5546`
- field/method proposals: **0**

## Rectangle union utility

- `rs/runelite/a/j` -> `RectangleUnion`
- `rs/runelite/a/j$c` -> `RectangleUnionRectangle`

The nested immutable value preserves the exact self-identifying form:

`RectangleUnion.Rectangle(x1=…, y1=…, x2=…, y2=…)`

It stores exactly four integer coordinates and is consumed by the outer utility.

The outer class has no instance state and exposes a static operation over a
`List<RectangleUnion.Rectangle>`. That operation constructs and returns a composite
`java.awt.Shape` representing the union of those rectangles.

The remaining nested sweep-line helper classes are deliberately left unnamed because their
developer-facing semantic identities are not preserved directly enough to meet this batch's
evidence standard.

## Acceptance boundary

Chat 2 does not promote R27. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_95A9F1C60A382FDF5546`.
