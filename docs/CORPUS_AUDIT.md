# Real-corpus acceptance audit

Synthetic tests protect individual trust boundaries. The corpus audit protects the
historical recovery assumptions against the real local client artifacts without committing
those binaries.

## Command

```powershell
spk-corpus-audit `
  C:\path\to\client-v307.jar `
  C:\path\to\client-v308.jar `
  C:\path\to\alternate-client.jar `
  --expect-previous-sha256 6232bae206846a4ba8d09766a2dee886b69016066a3f50f83b201bf705f93662 `
  --expect-current-sha256 854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6 `
  --expect-alternate-sha256 a9a5d1f35a6657b5c26939ca30e008748e718f6b206cc8fd93b64b57c4833385 `
  --expect-changed-same-path 1 `
  --expect-added-entries 0 `
  --expect-removed-entries 0 `
  --min-alternate-matches 1000 `
  --min-structural-or-better-matches 1000 `
  --max-alternate-unmatched-old 50 `
  --out .\generated\corpus-audit.json
```

The exact thresholds are explicit command-line policy rather than hidden constants.

The report contains:

- full input hash/index summaries
- previous -> current archive/class delta
- alternate -> current class matcher report
- every enforced expectation and whether it passed
- one final deterministic pass/fail result

Client JARs remain local. Only the optional JSON report may be retained, and even that
should be reviewed before publication if source filenames are sensitive.

This command is intentionally separate from `update-migrate`. It validates known corpus
behavior; it does not promote canonical lineage or create a new authority snapshot.
