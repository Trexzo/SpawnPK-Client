# Chat 2 — exact-v308 on-demand update hierarchy R63

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R63 is a separate non-canonical class-only semantic review batch recovering the classic
on-demand client update subsystem.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_BFEB6A18E65648025B67`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/cache/c` -> `CLIENT_CLASS_000096`
- `rs/cache/d` -> `CLIENT_CLASS_000097`
- `rs/cache/e` -> `CLIENT_CLASS_000098`

R25 already recovers the linked request-node base `rs/a` as `NodeSub`.

## `rs/cache/c` -> `OnDemandData`

This class extends `NodeSub` and is the concrete mutable request/result record consumed
by the fetcher.

Its compact state consists of request identifiers/status integers, booleans and the
downloaded `byte[]` payload. The fetcher queues, processes and returns this exact type.

That fixes the classic request-node identity `OnDemandData`.

## `rs/cache/d` -> `OnDemandFetcher`

The class:

- extends the parent class below;
- implements `Runnable`;
- owns socket, input/output streams and transfer buffers;
- owns CRC32 verification;
- owns multiple linked request/pending/completed queues;
- owns model/map/animation/MIDI CRC, version and index tables;
- runs the client update/request processing loop.

Exact surviving strings include:

- `model_crc`, `model_version`, `model_index`
- `anim_crc`, `anim_version`, `anim_index`
- `midi_crc`, `midi_version`, `midi_index`
- `map_crc`, `map_version`
- `Loading extra files - <n>%`
- `missing start of file`
- missing file/revision diagnostics
- `Rej: ...`

That is the exact on-demand update fetcher role.

## `rs/cache/e` -> `OnDemandFetcherParent`

The parent has only its constructor and one overridable no-op `a(int)` request hook.
`OnDemandFetcher` extends it directly.

Combined with the request-node and fetcher contracts, this reproduces the classic
`OnDemandFetcherParent` shim exactly.

## Naming boundary

These names are semantic/historical recovery names anchored by exact v308 structure and
behavior. Chat 2 does not promote them automatically.

## Acceptance boundary

Main/Core may accept any R63 subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_BFEB6A18E65648025B67`.
