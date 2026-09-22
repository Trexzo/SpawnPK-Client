# R3D reviewed new-member promotion

R3C intentionally leaves unmatched target-build members unresolved. That is necessary
because an unmatched member may be genuinely new code or simply a matcher miss.

R3D provides the explicit promotion step for members that have been reviewed and confirmed
to be genuinely new.

## Preconditions

A requested member can be promoted only when:

1. the target build already exists in canonical class lineage;
2. the exact target index SHA matches that canonical build;
3. the owner class has a canonical `CLIENT_CLASS_XXXXXX` location in the target build;
4. the exact member coordinate exists uniquely in the target index;
5. the same coordinate is currently recorded as `member_unmatched_new`;
6. the coordinate is not already owned by canonical member lineage.

Constructors and static initializers cannot be promoted into the renamable member
namespace.

## Stable IDs

Fields and methods maintain independent sequences:

```text
CLIENT_FIELD_000001
...
CLIENT_METHOD_000001
...
```

Promotion is deterministic regardless of the order in the review spec.

Promoted members begin with:

- `semantic_name = null`
- `semantic_status = UNKNOWN`
- relation `MANUAL`
- confidence `1.0`

Identity promotion does not infer a readable semantic name.

## Promotion spec

```json
{
  "schema_version": 1,
  "kind": "new_member_promotion_spec",
  "build_id": "v309",
  "authority": "RESEARCH",
  "note": "Reviewed exact v309 additions.",
  "members": [
    {
      "owner_logical_id": "CLIENT_CLASS_000123",
      "kind": "field",
      "name": "x",
      "descriptor": "I"
    },
    {
      "owner_logical_id": "CLIENT_CLASS_000123",
      "kind": "method",
      "name": "a",
      "descriptor": "(I)V"
    }
  ]
}
```

## Command

```powershell
spk-recovery member-promote-new `
  .\generated\v309.lineage.json `
  .\generated\v309.members.json `
  .\generated\v309-intake\new-index.json `
  .\generated\v309.new-members.review.json `
  --out .\generated\v309.members.promoted.json
```

Only the exact unresolved entries selected by the spec are removed. Everything else stays
available for later review.
