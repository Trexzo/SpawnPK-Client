# R2 Chat 2 — semantic to remap proposal bridge

R2A deliberately separates semantic labels from authorized bytecode remaps. Chat 2 now
mirrors that boundary with a one-way research bridge:

```text
semantic_name_candidate
        |
        v
stable CLIENT_CLASS logical ID
        |
        v
remap_spec_proposals   (research only)
        |
        X  no automatic conversion
        |
        v
remap_spec             (Chat 1 / explicit integration decision)
```

The proposal document uses the distinct kind `remap_spec_proposals`, so the R2A
`build_remap_plan` path cannot accept it as an authorized `remap_spec`.

## Exact v308 first proposal

The canonical R1 seed assigns exact-v308 `rs/i/b`:

`CLIENT_CLASS_000299`

The ordinal was independently checked against the exact v308 `rs/**` class ordering used
by the seed rule.

Chat 2 therefore proposes, but does not authorize:

```text
CLIENT_CLASS_000299
rs/i/b
  -> recovered/spawnpk/client/AdventureOrbRenderer
```

Confidence remains the semantic candidate confidence, `0.992872`, with exact resource,
literal-role and cross-build lineage provenance.

Member candidates such as `Client.a(J)V -> addFriend` are intentionally excluded from
this class bridge. They belong to R2C's eventual member-remap promotion boundary.
