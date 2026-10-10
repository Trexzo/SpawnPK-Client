# R11 — external canonical-method field witnesses (research only)

Existing R3M field_proof.py is unchanged: its strict canonical acceptance still counts own-field accesses in methods inside the declaring owner. R11 is a separate opt-in research-only evaluator; it does not generate an R3M proof or apply any mapping.

## Checks

- SHA-256 of original client JARs must match both build records and original indexes.
- CLI requires exact byte SHA-256 pins for both class-lineage and member-lineage JSON.
- Class and member lineage must validate; each profiled accepted class entry must match the recorded entry SHA-256.
- Only unresolved seeded fields in an accepted owner class are considered; target field declarations and access flags must exist and not already belong to another canonical member.
- Witness methods must have a genuine paired CLIENT_METHOD identity and consistent two-sided CLIENT_CLASS owner.
- Entire JVM instruction layouts **and all non-symbolic-CP decoded operands** must align, including local indexes, branch/switch targets, integer constants and increments. Symbolic CP referent identity outside the candidate field is not established by this research. Accessed field operation, offset, target-owner field ordinal and descriptor must align under only accepted class aliases. **Any rs/ object type in a field descriptor without an accepted class alias vetoes the witness**; it is never normalized to an untrusted wildcard, even when the raw obfuscated name is the same in both builds.
- At least two distinct accepted method IDs are required. Repeat accesses inside one method cannot satisfy the threshold.
- Divergent field accesses are retained as negative vetoes; swapping equally typed candidate fields must not produce accepted evidence.
- The result always has canonical=false, mapping_mutation=false and accepted_identities=0. Output files cannot be overwritten.

## Usage (private Windows checkout)

Set PYTHONPATH to the src directory and run python -m spk_recovery.external_field_witness_research_cli with --class-lineage, --class-lineage-sha256, --member-lineage, --member-lineage-sha256, --old-index, --new-index, --old-jar, --new-jar, --old-build-id v308, --new-build-id v309, --class-id CLIENT_CLASS_000141 and --out pointing to a new private JSON path. Read --help for argument syntax.

Original JARs, the generated report, obfuscated class/member coordinates, the R10/R11 private research evidence and recovered proprietary source must remain outside the public repository.

## Evidence and remaining gate

The separate SHA-pinned private R10/R11 investigation found three canonical-method witnesses each for CLIENT_FIELD_002107 and CLIENT_FIELD_002108. Its local proof-design test uses a minimal, privately derived class-lineage projection and is not a certified replay of the full original canonical class-lineage artifacts. Full accepted authority and external method-provenance checks remain required before a future change to R3M could authorize mapping promotion.

These matches are not claims of reflection, native linkage, class-initialization, exception, or whole-program equivalence. The previously reported 143 unresolved v309 fields and 26 descriptor blockers were not recomputed. This PR accepts zero identities.