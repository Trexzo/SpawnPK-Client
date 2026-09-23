# Chat 2 — exact-v308 GPU buffer pool / Mat4 R94

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R94 is a separate non-canonical class-only review batch for four GPU support identities that
have strong exact-v308 contracts and matching public source identities.

R93 remains intentionally unused as a semantic review number: the temporary R93 batch
duplicated R15 owners and was removed. Its only new finding, the stronger `SyncMode`
identifier for R15's `VsyncMode` proposal, is retained separately as research evidence.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_3F20064375FDD9C50616`
- field/method proposals: **0**

## Stable IDs

- `rs/k/b/a` -> `CLIENT_CLASS_000319` -> `BufferPool`
- `rs/k/b/b` -> `CLIENT_CLASS_000320` -> `FloatBufferCache`
- `rs/k/b/d` -> `CLIENT_CLASS_000322` -> `IntBufferCache`
- `rs/k/h` -> `CLIENT_CLASS_000337` -> `Mat4`

## BufferPool

Exact v308 owns:

- a `Stack<Long>` of native buffer addresses;
- a fixed byte-capacity;
- an allocation-state flag;
- the live GPU renderer owner.

Its contract is to preallocate reusable native blocks, free every stored address, accept
returned `IntBuffer` / `FloatBuffer` instances by converting them to addresses, and
recreate typed NIO views when a block is taken.

A public 117 HD RSPS client preserves `BufferPool` with the same native-memory contract,
field shape and typed put/take operations. SpawnPK adapts the owner from the HD plugin to its
GPU renderer, but the buffer-pool identity itself is unchanged.

## FloatBufferCache / IntBufferCache

The two v308 classes are access-ordered LinkedHashMap caches keyed by integer model hashes.

Each owns one BufferPool. Its `makeRoom` path removes the eldest cached buffer, returns
that native allocation to BufferPool and reports whether room was made. `clear()` drains
all cached buffers back into the pool.

Public 117 HD RSPS source preserves the exact names `FloatBufferCache` and
`IntBufferCache` with the same inheritance, constructor, make-room behavior and pooled
clear semantics.

## Mat4

Exact v308 `rs/k/h` is a stateless 4x4 matrix helper over `float[16]`.

It provides the same family of operations as RuneLite's GPU `Mat4`:

- identity;
- scale;
- translation;
- axis rotations;
- projection;
- in-place multiplication.

R87 GpuRenderer consumes these matrices for its OpenGL transform uniforms.

RuneLite preserves this class literally as
`net.runelite.client.plugins.gpu.Mat4`.

## Deliberate exclusions

R94 does not yet name:

- `rs/k/b/e`: ModelCache role is strong, but v308 adds a metadata-map superclass absent
  from the public reference used here;
- `rs/k/b/f`: ModelHasher role is plausible but the v308 field/hash surface differs from
  the available public revision;
- `rs/k/b/g`: TempModelInfo-like shape has additional pooling state in v308;
- `rs/k/m$a`: public `Shader.Unit` is structurally strong, but the generic simple name
  is being held until class-name collision/acceptance ergonomics are checked explicitly.

## Acceptance boundary

Chat 2 does not promote R94. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_3F20064375FDD9C50616`.
