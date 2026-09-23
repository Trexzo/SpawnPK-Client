# Chat 2 — exact-v308 stream and archive semantics R56

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R56 is a separate non-canonical class-only semantic review batch recovering the byte-stream,
archive and BZip2 layer used throughout the client.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_F6955D199D1E36C3F74D`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/x/a` -> `CLIENT_CLASS_001115`
- `rs/x/b` -> `CLIENT_CLASS_001116`
- `rs/x/e` -> `CLIENT_CLASS_001119`
- `rs/x/f` -> `CLIENT_CLASS_001120`

## `rs/x/e` -> `Stream`

This is the client's byte-buffer codec: byte array, mutable offset, bit-position state and
a large primitive read/write API covering integer widths, signed/unsigned variants,
strings, byte blocks, smart/variable values, bit access and cryptographic transforms.

Archive loaders, config definitions, graphics resources and networking all consume this
same type.

## `rs/x/f` -> `StreamLoader`

The constructor parses archive packed/unpacked lengths through Stream, optionally
decompresses the whole archive, then reads entry count and per-file hash/size/offset
metadata.

Named lookup uppercases the request and applies the classic rolling
`hash = hash * 61 + char - 32` rule. Entries are either copied from the already
decompressed archive or individually BZip2-decoded.

R55 IndexedImage/TextDrawingArea and many R28 definitions consume this class directly.

## `rs/x/a` -> `BZip2Decompressor`

StreamLoader directly invokes its public static decompression entry point. The method
initializes one shared decoder-state object and runs the private BZip2 bit reader,
selector/Huffman, move-to-front and block-reconstruction pipeline.

## `rs/x/b` -> `BZip2DecompressionState`

This object is the dedicated mutable state for BZip2Decompressor. Its fields are the exact
working structures expected by that decoder: input/output buffers, bit counters,
in-use/selector arrays, frequency/cumulative tables, Huffman limit/base/perm arrays and
block scratch data.

## Deliberately withheld adjacent helpers

`rs/x/c` and `rs/x/d` form a small timestamp/count tracking structure but are not part
of the archive/stream contract above; R56 leaves them unnamed.

## Naming boundary

These are semantic/historical recovery names grounded in exact v308 behavior. They remain
non-canonical candidates.

## Acceptance boundary

Chat 2 does not promote R56. Main/Core may accept any desired subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_F6955D199D1E36C3F74D`.
