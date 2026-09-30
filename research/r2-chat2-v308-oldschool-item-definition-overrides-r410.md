# Chat 2 — exact-v308 OldSchool item definition overrides R410

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/c/a/a` -> `CLIENT_CLASS_000080` -> `OldSchoolItemDefinitionOverrides`
- proposal: `SEMPROP_213778F492F005BD153D`
- review: `SEMREVIEW_1ABDCE274ED42667B0B0`

## Exact dependency

The class mutates only `rs/d/r` definition instances. The target definition owns
item-style name/action/model state plus ID lookup/decode behavior.

The dependency is bidirectional:

- `rs/c/a/a` -> `rs/d/r`
- `rs/d/r` -> `rs/c/a/a`

## Exact mode gate

The definition finalize path invokes this override table only when the active
`rs/d/r$a` enum value is **OLDSCHOOL**.

The same enum separately contains:

- STANDARD
- OLDSCHOOL
- NEW
- OSRS

So the table is not a generic all-mode patch layer.

## Override surface

The class contains a very large ID switch and mutates exact definition state including:

- action arrays;
- model/variant arrays;
- copied definition state;
- other presentation fields.

## Boundary

The name is descriptive exact-v308 behavior, not a claim that the stripped developer class
was literally named this way.

R410 remains non-canonical Chat 2 research.
