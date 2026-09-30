# Chat 2 — exact-v308 chunk rotation R409

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/c` -> `CLIENT_CLASS_000079` -> `ChunkRotation`
- proposal: `SEMPROP_705293D1848C16E6E204`
- review: `SEMREVIEW_042DD2FB7D6B6A3D16D7`

## Exact behavior

The class is a pure coordinate utility with four static helpers.

Two helpers rotate one local x/y point inside an 8x8 chunk. Rotation is masked with
`& 3` and the four orientations use the standard transforms involving `7 - x` /
`7 - y`.

The two five-argument helpers perform the same rotation while accounting for rectangular
object width/height, subtracting `dimension - 1` on orientations where the footprint
extends back from the rotated anchor.

## Boundary

The behavior is exact, but no trustworthy original historical class name was recovered.
`ChunkRotation` is therefore descriptive rather than presented as a verbatim developer
identifier.

R409 remains non-canonical Chat 2 research.
