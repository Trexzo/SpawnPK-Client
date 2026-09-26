# Chat 2 — exact-v308 stream and compression semantics R29

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R29 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R28 review batches.

## Deterministic review result

- candidate classes: **5**
- resolved proposals: **5**
- unresolved: **0**
- review ID: `SEMREVIEW_058934E269FB8E9BAFBF`
- field/method proposals: **0**

## Stream + ISAAC

- `rs/x/e` -> `Stream`
- `rs/q/a` -> `IsaacCipher`

`Stream` extends the R25 `NodeSub` identity and owns the classic byte payload,
offset/bit-position state and a very broad primitive/string/byte-array read/write surface.

It also carries the RSA path through `BigInteger`, and its opcode writer adds the next
integer from `rs/q/a` before storing the opcode byte.

`IsaacCipher` is fixed by the standard ISAAC algorithm:

- two 256-int arrays;
- accumulator/counter state;
- golden-ratio initialization constant `-1640531527`;
- standard ISAAC mix/generation shifts;
- one pseudorandom integer emitted per call.

The Stream dependency confirms its packet-opcode cipher role.

## Archive loading

- `rs/x/f` -> `StreamLoader`

This class parses the classic archive header through Stream, stores per-entry name hashes,
sizes and offsets, and retrieves files by the historical uppercase hash*61 algorithm.

Whole archives may be:

- stored uncompressed;
- BZip2-compressed;
- or GZIP-compressed in this SpawnPK lineage.

Its structure and lookup behavior match the classic StreamLoader family exactly.

## BZip2

- `rs/x/a` -> `BZip2Decompressor`
- `rs/x/b` -> `BZip2State`

`BZip2Decompressor` exposes the static byte-array decompression entrypoint used by
StreamLoader and implements the BZip2 bit/Huffman/block pipeline over one shared state
object.

`BZip2State` owns the characteristic BZip2 state:

- input/output positions and counters;
- 256/257 symbol tables;
- 16 group-used flags;
- selector arrays;
- six Huffman limit/base/permutation tables;
- large block buffers and decode counters.

These names are semantic recovery, not a claim that exact original source identifiers
survived unchanged.

## Acceptance boundary

Chat 2 does not promote R29. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_058934E269FB8E9BAFBF`.
