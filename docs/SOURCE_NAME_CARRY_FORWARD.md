# R6E source-name carry-forward

R6E transfers **previously accepted inferred parameter/local names** into a regenerated
or future-build recovered-source workspace without treating source offsets or old
`SRC_*` IDs as persistent identity.

## Trust boundary

Carry-forward requires stable canonical method identity. The transfer anchor is:

```text
CLIENT_METHOD_* + symbol kind + ordinal + declared type
```

The whole method's source-symbol shape must also remain unchanged:

```text
(kind, ordinal, declared type) for every source symbol in the method
```

If that shape changes, the method returns to semantic review even when one individual
parameter/local still appears to match.

### Same exact build regeneration

Allowed only when both source inventories are tied to the same exact binary authority SHA.

### Cross-build transfer

Additionally requires R3 delta reports proving:

- owner class is byte-identical or structurally equivalent
- method shape is unchanged or only its obfuscated member name changed

Modified, missing, ambiguous, type-shifted, or colliding symbols are blocked.

## Output

`spk-source-name-carry-forward` writes:

- `source-name-carryforward.json`
- `source-name-candidates.json` when safe transfers exist
- `source-name-review.json`
- `source-name-acceptance.json` for previously accepted names that re-prove safely
- `source-rename-plan.json`

The transferred names remain inferred replacements. They are never presented as recovered
original local/parameter names.

## Example

```powershell
spk-source-name-carry-forward `
  .\authority\v308-source-rename-plan.json `
  .\authority\v308-source-symbols.json `
  .\generated\v309-source-symbols.json `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  --class-delta .\generated\v308-to-v309.class-delta.json `
  --member-delta .\generated\v308-to-v309.member-delta.json `
  --out-dir .\generated\v309-source-name-carryforward
```

Exit code 0 means every previously accepted name was safely carried or was already present.
Exit code 3 means the process completed but at least one symbol was blocked for fresh review.
