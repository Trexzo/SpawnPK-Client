# Chat 2 — exact-v308 node hash table semantics R52

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R52 is a separate non-canonical class-only semantic review batch extending R25's linked-node
recovery.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_DBF7A67588D8C75AB96E`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/o` -> `CLIENT_CLASS_000685`

R25 already recovered:

- `rs/t` -> `Node`

## `rs/o` -> `NodeHashTable`

The constructor allocates exactly 1024 `Node` sentinel records and self-links each sentinel's
primary previous/next pointers.

Lookup:

1. masks the requested long key with `bucketCount - 1`;
2. selects the corresponding sentinel bucket;
3. walks the primary linked-node chain;
4. compares each R25 Node's long key;
5. returns the matching Node or null.

Insertion:

1. unlinks the Node from any existing primary chain;
2. selects a bucket using the same key mask;
3. splices the Node into the sentinel's list;
4. stores the supplied long key into the Node key field.

That is exactly a fixed-bucket keyed Node hash table. The proposed semantic name is
`NodeHashTable`.

## Naming boundary

This is a semantic recovery name. R52 does not claim it is a verbatim original SpawnPK
developer identifier.

## Acceptance boundary

Chat 2 does not promote R52. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_DBF7A67588D8C75AB96E`.
