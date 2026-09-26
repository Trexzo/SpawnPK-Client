# Chat 2 — exact-v308 117 HD model-cache lineage R95

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R95 is a separate non-canonical class-only review batch for the remaining exact-v308
`rs/k/b/*` model-cache family.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_7521F7FDA263E7AEE914`
- field/method proposals: **0**

## Stable IDs

- `rs/k/b/c` -> `CLIENT_CLASS_000321` -> `ModelData`
- `rs/k/b/e` -> `CLIENT_CLASS_000323` -> `ModelCache`
- `rs/k/b/f` -> `CLIENT_CLASS_000324` -> `ModelHasher`
- `rs/k/b/g` -> `CLIENT_CLASS_000325` -> `TempModelInfo`

## ModelData

Exact v308 contains exactly:

- one `int[]` data field;
- one integer face-count field;
- fluent setters;
- a face-count getter;
- a two-index lookup equivalent to `colors[(face * 4) + index]`.

Public 117 HD source preserves `ModelData` with the same fields, fluent API and exact
four-integers-per-face lookup. This is effectively an exact semantic/source-shape match.

## ModelCache

Exact v308 combines two public 117 HD ModelCache generations in one class.

The first responsibility is the older native buffer-cache manager:

- BufferPool;
- IntBufferCache;
- two FloatBufferCache instances;
- vertex / normal / UV get+put;
- typed native-buffer acquisition;
- weighted `makeRoom()`;
- clear/shutdown.

It even preserves the distinctive older diagnostic:

`defaulting model cache to 512MiB due to non 64-bit client`

The second responsibility is the newer model metadata cache:

`LinkedHashMap<Integer, ModelData>`

Current public 117 HD source preserves `ModelCache extends LinkedHashMap<Integer, ModelData>`,
while older public revisions preserve the native buffer-cache implementation.

SpawnPK v308 has merged those two historical ModelCache responsibilities into
`rs/k/b/e`. The semantic identity is therefore stronger than matching either revision
alone.

## ModelHasher

Exact v308 owns:

- one model reference;
- six integer hashes corresponding to model color/transparency/texture surfaces;
- an `Arrays.hashCode` color/cache hash that includes model override amount, hue,
  saturation and luminance;
- another model-array hash path.

Public 117 HD `ModelHasher` preserves the same model + six-hash structure and the same
`Arrays.hashCode` color/batch-hash lineage.

The v308 setter path is locally simplified and does not visibly rebuild all six hashes in
the same way as the public revision, so R95 uses confidence **0.998** rather than claiming
source equivalence.

## TempModelInfo

Exact v308 has the same three instance values and fluent API as public 117 HD
`TempModelInfo`:

- temporary vertex offset;
- temporary UV offset;
- face count.

SpawnPK adds a local 6048-entry preallocated object pool and integer-keyed lookup around
those same instances. The pooling layer does not alter the underlying TempModelInfo data
contract.

## Relationship to R94

R94 recovered the shared lower-level support:

- BufferPool
- FloatBufferCache
- IntBufferCache
- Mat4

Together R94 + R95 explain the full exact-v308 `rs/k/b/*` cache support family except for
no additional unnamed sibling in that package.

## Acceptance boundary

Chat 2 does not promote R95. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_7521F7FDA263E7AEE914`.
