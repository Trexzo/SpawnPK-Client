# v309 cross-lane class evidence priorities

The accepted v309 global field report has **143 unresolved fields**:

- 26 `descriptor_identity_guard_rejected`
- 68 `empty_both`
- 48 `global_class_topology_guard_rejected`
- 1 `raw_source_guard_rejected`

The 26 descriptor vetoes depend on eight old canonical class identities
whose new-build identities are not proven. The read-only cross-lane analysis
tests how many additional topology vetoes would look equal **if** a
descriptor-derived raw class spelling were substituted for an old canonical
class label. This substitution is an *explicitly unproven hypothesis*,
not an identity match or acceptance.

Run with the exact accepted GitHub frontier (no private JARs necessary):

```powershell
python -m spk_recovery.v309_crosslane_class_impact `
  --out "$env:TEMP\v309-class-impact-research-new.json"
```

This refuses a mutated/unpinned source report, rejects duplicate malformed
field topology and review outcomes, and never overwrites a report file.

## Pinned observational priority (not proof)

The current tracked report yields:

| Hypothetical class | Descriptor-blocked fields | Other topology-blocked fields equal under this alias **alone** | Combined research priority |
| --- | ---: | ---: | ---: |
| `CLIENT_CLASS_000029 → RAW:rs/Client` | 14 | 31 | **45** |

The same raw `rs/Client` symbol appears as a **new** source-class label
in 39 topology-veto records that include the old canonical Client label.
Only **31** of those records become structurally equal by substituting
that alias alone; the other eight have additional differences. Therefore
39 must **not** be reported as 39 automatically resolved fields.

Across all eight descriptor-derived alias hypotheses, **34 of the 48**
topology-veto records become structurally equal *in the counterfactual
report comparison*. The other **14** remain mismatched. None of those 34
is a proven field identity, and the existing bytecode, class-lineage,
global-topology, and explicit member-acceptance gates remain mandatory.

The purpose is to **prioritize the exact private-JAR class witness** for
`CLIENT_CLASS_000029`, since its outcome might affect more residual
evidence than treating 26 descriptor and 48 topology fields in isolation.

A PASS is always labeled
`HYPOTHETICAL_NORMALIZATION_NOT_CLASS_IDENTITY_PROOF`.

The accepted unresolved count remains 143 until real independent class
proof, recomputation of affected field evidence, explicit reviewed
member-identity acceptance and ordinary GitHub CI certify a different
frontier. Do not commit proprietary JARs or raw private indexes.
