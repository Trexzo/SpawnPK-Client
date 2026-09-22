# R3G — conservative update delta classification

Identity and change are separate questions.

R1/R3 matching answers:

> Is this the same logical class/member across builds?

R3G answers:

> Given that identity relationship, what changed in the indexed evidence?

The classifier deliberately avoids stronger claims than the index can prove.

## Class classifications

- `byte_identical` — exact class-entry SHA-256 is unchanged.
- `structurally_equivalent` — name-insensitive structural fingerprint is unchanged, even
  if the class entry/path bytes differ.
- `constant_payload_candidate` — declaration metadata is unchanged while indexed literal
  and/or numeric constant pools changed. This is a focused-analysis classification, **not**
  proof that source code changed only a single constant.
- `modified_class` — the indexed evidence changed beyond those conservative cases.

Each matched class also records whether its obfuscated path moved and which evidence
dimensions remained equal.

## Member classifications

Member deltas consume an explicit member-identity candidate report.

- `member_only_obfuscation_rename` — member spelling changed while descriptor shape,
  access and code length remain stable.
- `member_shape_unchanged` — name/descriptor/access/code length remain unchanged.
- `modified_member` — one or more of those indexed dimensions changed.
- `new_member_candidate` — unmatched on the target side; not automatically promoted.
- `removed_member_candidate` — unmatched on the old side; not automatically treated as
  definitively removed code.

These are evidence classifications. They do not authorize canonical identity transfer,
semantic-name acceptance, or bytecode rewriting.

## Migration workspace

`update-migrate` now writes:

```text
delta-report.json
```

alongside the existing R3F workspace outputs.

The workspace manifest also includes `class_delta_summary` and
`member_delta_summary`, so a future release can be triaged without opening every class.

The authority gate remains unchanged: delta labels never bypass unresolved/promotional
review requirements.
