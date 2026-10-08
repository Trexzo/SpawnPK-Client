# v309 descriptor replay: offline consistency review

This is a **research-only continuation** of the exact-JAR class-witness pipeline
merged in PRs #862–#865. It does not eliminate the need for the two exact
proprietary client JARs or independently validate their bytecode.

## When to use

After a local operator has run
`python -m spk_recovery.descriptor_class_private_jar_replay`
with the two pinned exact JARs and received a new research report, it is
possible to review the **self-consistency** of the small report against the
tracked accepted-incomplete GitHub frontier without uploading private binaries
or full indexes.

The replay report still contains class names, fingerprints, and relationship
identifiers. Treat it as **private research evidence** until reviewed for
publication; do not automatically commit or share it.

```powershell
python -m spk_recovery.descriptor_class_replay_offline_review `
  --replay "C:\private\v309-class-witness-result.json" `
  --out "$env:TEMP\v309-class-consistency-new.json"
```

The command defaults to these tracked sources relative to the project root:

- `research/v309-field-recovery/frontier.json`
- `research/v309-field-recovery/class-lineage.json`
- `research/v309-field-recovery/global-field-usage.json`

It verifies the tracked source file SHA-256 values against the accepted frontier,
the exact v308/v309 build hashes, deterministic research report digest and
class/field accounting, supported proof strategies and rejection reasons,
uniqueness of proposed targets, and the original 26 blocked relationships
across 8 class dependencies. It refuses to overwrite any input or an existing
output.

## What a PASS does *not* mean

The offline verifier **cannot** rerun exact-JAR indexing, prove that class
fingerprints actually came from the proprietary clients, or establish global
hash uniqueness. A fabricated but internally consistent report can pass.
Therefore it deliberately labels its result:

`CONSISTENCY_ONLY_NOT_INDEPENDENT_PROOF_NO_IDENTITIES_ACCEPTED`

The actual private replay must be measured locally, class witnesses must be
independently reviewed, and dependent field evidence must be recomputed before
any identity acceptance. The canonical member frontier remains **143 unresolved**
until a separate reviewed acceptance is committed and all fail-closed gates pass.
