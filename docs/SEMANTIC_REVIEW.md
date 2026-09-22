# R2C2 semantic review and explicit promotion

Semantic recovery is allowed to be exploratory. Canonical naming is not.

Chat 2 may produce high-confidence English-name candidates from bytecode, packets,
resources, cache/config evidence and cross-build persistence. Those candidates remain
research output until Chat 1 verifies their exact build coordinates and the user/project
explicitly selects which reviewed proposals become canonical.

## Flow

```text
semantic_candidate_set          (research / non-canonical)
        |
        | semantic-resolve
        v
semantic_review_set             (stable IDs + proposal IDs)
        |
        | explicit semantic_acceptance_spec
        v
canonical class/member lineage  (semantic_status = ACCEPTED)
```

### Resolve

`semantic-resolve` verifies:

- exact source build exists in canonical class lineage
- candidate source SHA equals that build's exact client SHA
- class coordinates resolve to one stable `CLIENT_CLASS_XXXXXX`
- field/method coordinates resolve to one stable `CLIENT_FIELD_XXXXXX` or
  `CLIENT_METHOD_XXXXXX`
- proposed names are valid Java identifiers

Each valid proposal receives a deterministic `SEMPROP_<hash>` identifier. The complete
proposal set receives a deterministic `SEMREVIEW_<hash>` review ID.

No canonical state is changed.

### Accept

`semantic-accept` requires a separate acceptance document containing:

- the exact `SEMREVIEW_*` ID
- an explicit list of `SEMPROP_*` IDs to accept

The command rejects stale review IDs, unknown proposal IDs, duplicate selections and
semantic-name collisions.

Accepted names are stored with the original proposal evidence, exact build SHA and source
coordinate. They are behavior-oriented recovered names; they are not claimed to be the
lost original developer identifiers.

## Example acceptance spec

```json
{
  "schema_version": 1,
  "kind": "semantic_acceptance_spec",
  "review_id": "SEMREVIEW_0123456789ABCDEF0123",
  "accept": [
    "SEMPROP_0123456789ABCDEF0123"
  ]
}
```

This stage still does **not** rewrite bytecode. R2C3 will translate accepted member names
into a verified member-remap plan consumed by the ASM repackager.
