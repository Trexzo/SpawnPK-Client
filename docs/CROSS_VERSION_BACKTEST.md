# Cross-version recovered-source backtest

The cross-version backtest proves that the recovery pipeline is not tied to one exact client postimage.

It consumes authority artifacts that already passed their own recovery gates. It does **not** decompile a client, mutate mappings, accept semantic names, or publish recovered source.

## Inputs

Required:

- old `recovery_release_manifest`
- new `recovery_release_manifest`
- `update_intake_report` linking the same old/new exact authority pair
- `semantic_carryforward_report` linking the same old/new pair

Optional:

- `source_name_carryforward_report`
- exact migration-summary expectations

Both recovery release manifests must independently report `ready_for_release=true` and expose their exact `final_source_tree_sha256`. The backtest ID binds both recovered source-tree hashes as well as both client authorities. The update intake and semantic carry-forward report must bind the exact same build IDs and SHA-256 authorities. The semantic carry-forward namespace must equal the new release namespace.

When a source-name carry-forward report is supplied, it becomes a required part of the proof and must bind the same build/SHA pair with `full_carryforward_ready=true`.

## Command

First build the exact archive-level delta from the private JARs:

```powershell
spk-cross-version-binary-delta `
  .\private\v307-client.jar `
  .\private\v308-client.jar `
  --old-build-id v307 `
  --new-build-id v308 `
  --out .\v307-to-v308\binary-delta.json
```

Then bind that binary authority into the recovered-source backtest:

```powershell
spk-cross-version-backtest `
  .\v307\recovery-release.json `
  .\v308\recovery-release.json `
  .\v307-to-v308\migration-report.json `
  .\v307-to-v308\semantic-carryforward.json `
  --source-name-carryforward .\v307-to-v308\source-name-carryforward.json `
  --binary-delta .\v307-to-v308\binary-delta.json `
  --expectations .\fixtures\v307-v308-cross-version-expectations.json `
  --out .\v307-to-v308\cross-version-backtest.json
```

The binary-delta command hashes both exact JARs, rejects duplicate ZIP entry names, and records only old-only/new-only/changed entry metadata; unchanged entry payloads are not copied into its JSON output.

A passing backtest exits `0`. A well-formed but failed proof exits `2`. Malformed or unsupported authority input is rejected before a report is accepted.

## Expectations

The optional expectations JSON is intentionally narrow. Supported exact keys:

```json
{
  "old_scope_classes": 0,
  "new_scope_classes": 0,
  "matched_classes": 0,
  "class_identity_reuse_percent": 0.0,
  "changed_same_path_classes": 0,
  "analysis_queue_items": 0,
  "ambiguous_classes": 0,
  "unmatched_old_classes": 0,
  "unmatched_new_classes": 0,
  "changed_same_path_class_paths": [],
  "classifications": {},
  "class_delta_summary": {}
}
```

Only include metrics that are independently justified for the fixture. The backtest fails if an expected value drifts.

## Intended first historical fixture

The first intended private backtest is the historical SpawnPK v307 -> v308 transition:

- historical v307 SHA-256: `6232bae206846a4ba8d09766a2dee886b69016066a3f50f83b201bf705f93662`
- exact v308 SHA-256: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

The actual client JARs and recovered/generated source remain outside public Git. The historical hashes are fixture provenance, not a substitute for supplying and independently verifying the exact binary artifacts.

Exact private-byte inspection of the saved historical pair establishes the intended update-intake expectations:

```json
{
  "old_scope_classes": 1129,
  "new_scope_classes": 1129,
  "matched_classes": 1129,
  "class_identity_reuse_percent": 100.0,
  "changed_same_path_classes": 1,
  "analysis_queue_items": 0,
  "ambiguous_classes": 0,
  "unmatched_old_classes": 0,
  "unmatched_new_classes": 0,
  "changed_same_path_class_paths": [
    "rs/f/a.class"
  ],
  "classifications": {
    "byte_identical_same_path": 1128,
    "structurally_equivalent_same_path": 1
  },
  "class_delta_summary": {
    "byte_identical": 1128,
    "structurally_equivalent": 1,
    "matched_classes": 1129,
    "path_moved": 0,
    "ambiguous_classes": 0,
    "unmatched_old_classes": 0,
    "unmatched_new_classes": 0
  }
}
```

The structural classifier intentionally ignores instruction immediates, so the one changed class remains structurally equivalent even though its exact bytecode changes the build constant from 307 to 308. This is identity evidence, not a claim of byte-identical behavior.

## Alternate-obfuscation fixture: v305 -> v308

The Library also contains exact alternate-lineage archive
`a9a5d1f35a6657b5c26939ca30e008748e718f6b206cc8fd93b64b57c4833385`.
The cross-build matcher maps its build/config class `rs/g/a` to v308
`rs/f/a`; the old bytecode contains build constant 305.

This is the harder regression fixture. Its independently reproduced current matcher surface is:

- 1,099 -> 1,129 `rs/` classes;
- 1,074 matched old identities (97.7252%);
- 513 exact-SHA matches;
- 533 structural-unique matches;
- 23 package-anchor research candidates;
- 5 weighted mutual-best candidates;
- 10 ambiguous;
- 25 unmatched old / 55 unmatched new;
- 118 focused review-queue items.

The raw archive delta authority for this pair is
`XVERBIN_C5DDFB581E208052ADF6`: 10,939 -> 10,970 entries, 246 old-only,
277 new-only, 372 changed entries, of which 370 are class entries.

The exact expected machine-readable metrics live in
`fixtures/v305-v308-cross-version-expectations.json`. This fixture is
expected to remain partially unresolved at the intake stage; the purpose of the
later recovered-source backtest is to prove that reviewed/canonical lineage and
semantic carry-forward can bridge that harder obfuscation transition without
inventing identity.

## Truth boundary

A PASS means:

1. both exact builds independently produced release-ready recovered source;
2. the migration artifact binds that exact old/new authority pair;
3. accepted semantic identity survives according to the canonical carry-forward gate;
4. optional inferred source-name carry-forward also survives when required;
5. supplied regression expectations match exactly.

It does not prove that inferred parameter/local names are original developer identifiers, and it does not weaken any Source M1 clean-build or round-trip gate.
