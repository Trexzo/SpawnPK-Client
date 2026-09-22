# R6B inferred source-name candidate review

R6B defines the intelligence boundary for source-level parameter/local naming.

Candidate producers target stable R6A `source_symbol_id` values. They must not use raw
decompiler variable text or line numbers as persistent identity.

## Candidate rules

Each candidate supplies:

- `source_symbol_id`
- one proposed Java identifier
- confidence in `[0, 1)`
- non-empty evidence
- optional note

Confidence **1.0 is forbidden** because the original parameter/local text was stripped
from exact v308. These are inferred readable replacements.

Java keywords/reserved names, unknown symbols and no-op proposals are rejected.

## Review resolution

`spk-source-name-review` validates a candidate set against one exact source inventory.

- exact duplicate candidate rows collapse deterministically;
- multiple rows agreeing on one name become one reviewable proposal;
- different names for the same symbol become an explicit conflict;
- no source file is changed;
- no proposal becomes canonical automatically.

The output assigns deterministic `SRCCAND_*`, `SRCPROP_*` and `SRCREVIEW_*` IDs.

## CLI

```powershell
spk-source-name-review `
  .\source-symbols.json `
  .\source-name-candidates.json `
  --out .\source-name-review.json
```

R6C will consume explicit proposal acceptance and perform collision/shadowing validation
before deterministic source rewriting.
