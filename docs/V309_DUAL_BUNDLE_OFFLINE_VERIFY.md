# v309 dual evidence bundle — offline consistency verifier

This step checks a locally generated **three-file research bundle** from
`v309_private_dual_proof_replay` against the accepted GitHub v309 frontier.
It does **not** independently rerun either private client JAR or establish
class/member mapping authority.

## Local use

From the installed `SpawnPK-Client` repository:

```powershell
python -m spk_recovery.v309_dual_bundle_offline_verify `
  --bundle-dir "$env:TEMP\spk-v309-dual-proof-new"
```

The input directory must contain **only** the three files written by the exact
private replay: `BUNDLE.json`, `descriptor-class-research.json`, and
`empty-field-declaration-research.json`. This verifier writes no output
files and prints only a compact summary.

It SHA-256-verifies the three tracked source files (class lineage, member
lineage, global report) against `frontier.json`. It checks both private-build
hash labels and the complete 26-descriptor / 8-class and 68-empty-field group
membership. The bundle manifest must bind both research reports by their full
deterministic digests. The verifier also checks the exact blocked relationship
IDs, target owner/class labels, rejection accounting and report ID material,
while refusing unknown authority/acceptance fields.

This is an **internally consistent JSON review, not private-bytecode proof**.
An internally consistent forged report can pass, including a synthetic
candidate that was never established from the JARs. Results are always labeled:

`CONSISTENCY_ONLY_NO_PRIVATE_JAR_PROOF_NO_IDENTITIES_ACCEPTED`

No class/member lineage is changed, no mappings are accepted, and the
accepted **143 unresolved** frontier remains authoritative until the
separate independent exact-JAR evidence and explicit acceptance gates succeed.
Do not automatically commit the private research bundle to GitHub.
