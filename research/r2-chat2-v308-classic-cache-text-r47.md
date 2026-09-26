# Chat 2 — exact-v308 classic node-cache and text semantics R47

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R47 is a separate non-canonical class-only semantic review batch. Exact v308 behavior is
the authority; public 317-era sources are used only as historical/cross-structural
corroboration.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_9BF3AD4F6D29C99D0FD8`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/B` -> `CLIENT_CLASS_000027`
- `rs/F` -> `CLIENT_CLASS_000033`
- `rs/O` -> `CLIENT_CLASS_000042`
- `rs/P` -> `CLIENT_CLASS_000043`

## `rs/B` -> `NodeSubList`

The class owns one sentinel R25 `NodeSub` and one traversal cursor.

The sentinel's two NodeSub links initially point to itself. The methods then implement:

- insert-at-head, unlinking an already-linked node first;
- pop/unlink tail;
- reverse-iteration begin;
- reverse-iteration continue;
- node count.

This is the exact classic intrusive `NodeSubList` shape.

## `rs/F` -> `MruNodeCache`

The class combines:

- a fixed capacity;
- remaining-space counter;
- sentinel NodeSub;
- R47 NodeSubList for recency order;
- a long-keyed node table.

A cache hit is promoted to the list head. On insertion at full capacity, the least-recently
used tail is popped and unlinked from both node structures before the new entry is inserted
and promoted.

The historic client calls the same structure `MRUNodes`. R47 uses `MruNodeCache` because
that states the proven behavior directly.

## `rs/O` -> `TextClass`

Exact v308 preserves the classic helper family:

- base-37 player-name -> long;
- long -> base-37 player name;
- sprite-name hash;
- integer address -> dotted-quad string;
- underscore/name capitalization normalization;
- asterisk masking.

The method family and base-37 constants match classic `TextClass` directly.

## `rs/P` -> `TextInput`

The class owns a fixed legacy chat alphabet, reusable character buffer and reusable Stream.
It:

- truncates outgoing text to 80 characters;
- lowercases it;
- maps characters through the fixed alphabet;
- decodes stored alphabet indices;
- sentence-capitalizes after period/exclamation/question marks;
- exposes a reusable encode/decode normalization round trip.

Classic `TextInput` has the same alphabet and high-level codec role. v308 no longer uses
the older nibble-packing wire algorithm in this class; it writes direct character-table
indices. The name therefore captures historical/semantic lineage, not byte-for-byte
algorithm identity.

## Acceptance boundary

Chat 2 does not promote R47. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_9BF3AD4F6D29C99D0FD8`.
