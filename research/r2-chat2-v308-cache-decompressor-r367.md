# Chat 2 — exact-v308 cache Decompressor R367

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/cache/a` -> `CLIENT_CLASS_000082` -> `Decompressor`
- proposal: `SEMPROP_23B91870D52B11FE81FA`
- review: `SEMREVIEW_6A96E3D80E1472066489`

## Exact cache layout

The class owns a shared **520-byte** sector buffer and two RandomAccessFile handles:

- cache data file;
- cache index file.

The index entry is exactly **6 bytes**:

- 3-byte file length;
- 3-byte first-sector id.

Each data sector is **520 bytes**:

- 8-byte sector header;
- up to 512 bytes payload.

The sector header contains the expected file id, chunk number, next-sector pointer and
store/archive id. Reads validate those fields before following the sector chain.

The write path implements the corresponding index entry and chained-sector layout.

## Original identity

Public 317 client sources preserve this exact structure under the class name
`Decompressor`: data/index RandomAccessFiles, six-byte index records, 520-byte sectors,
eight-byte headers and 512-byte payload chunks.

This is therefore an original legacy client identity rather than a descriptive invented
cache name.

## Boundary

The surrounding `rs/cache/b` manager owns multiple cache stores and file handles, but its
original class-level identity is not independently fixed here.

R367 remains non-canonical semantic research only.
