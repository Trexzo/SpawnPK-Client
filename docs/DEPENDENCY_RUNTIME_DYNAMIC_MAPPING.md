# R8DEP31 dynamic-only structural replacement proof

R8DEP31 examines only R8DEP30 `dynamic_mapping_authority_gap` classes.

It reuses the exact bundled-class and official-artifact parsing authority from
R8DEP5, but deliberately accepts only the narrow structural mapping forms:

- same internal name with exact structural SHA equality;
- unique 1:1 structural SHA match across bundled and official class sets.

Package-name similarity, API-shape package inference, topology inference,
confidence scores, and readable-name similarity are not authority in this lane.

Accepted class mappings are additionally required to have equal ordered field
sequences and equal ordered ordinary-method structural sequences.

Even then, the result is only **class mapping authority**. It does not invent
field/method names or descriptors and it does not mutate DEPREPLACE.

Every accepted class mapping therefore reports
`member_authority_required=true`, and the report keeps
`ready_for_dynamic_root_promotion=false`.

Outputs distinguish:

- accepted class mapping;
- ambiguous structural match;
- no official structural match.

Public output is identifier-redacted. Private output may contain exact old/new
owners, artifact binding, structural SHA and candidate counts.

No runtime mutation or dependency pruning occurs in R8DEP31.
