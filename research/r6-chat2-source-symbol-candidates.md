# Chat 2 — R6 source-symbol intelligence handoff

R6A inventories deterministic source-level parameter/local identities. Core R6B now owns
the canonical non-mutating review mechanics:

- `source_name_candidate_set`
- deterministic `SRCCAND_*` candidate IDs
- deterministic `SRCPROP_*` proposal IDs
- deterministic `SRCREVIEW_*` review IDs
- Java-identifier/no-op validation
- exact candidate deduplication
- explicit conflicting-name reporting

Chat 2 therefore does **not** maintain a parallel source-name review engine.

## Chat 2 ownership from R6B onward

Chat 2 should produce evidence-backed candidate rows targeting stable R6A
`source_symbol_id` values.

Candidate generation should prefer:

- canonical method semantics from accepted/reviewed `CLIENT_METHOD_*` identities;
- exact type/data flow;
- exact API roles;
- exact use sites;
- literal/control-flow associations;
- surrounding recovered-source context.

The original client stripped source parameter/local names, so these are readable inferred
replacement names rather than recovered original identifiers.

## Core handoff

Chat 2 output should conform directly to core R6B's:

`source_name_candidate_set`

and then be resolved using:

`spk-source-name-review`

Chat 2 must not:

- mark source names accepted;
- rewrite Java source;
- modify the source-tree authority hash;
- bypass source-scope collision/shadowing validation.

Those belong to the core R6C+ acceptance/rewrite path.

## Confidence rule

Inferred source names must remain below certainty. Chat 2 should treat confidence as
evidence strength, not as proof of an original source identifier.

The useful next Chat 2 step is an evidence producer that can inspect one R6A source-symbol
inventory plus the verified recovered source tree and emit reviewable candidate rows
without altering either input.
