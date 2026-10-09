# v309: pinned accepted-owner CP corroboration (research only)

The merged exact-private five-lane engine (#890) deliberately normalizes the
proposed class's own obfuscated name only. It does not assume any third-party
class identity. This is safe, but it understates CP-method continuity when a
referenced class has **already been accepted** as the same canonical logical
class across exact v308 and v309.

This narrow, independent research CLI addresses one concrete remaining
blocker: `CLIENT_CLASS_000943`. It is **not** a modification to the official
five-lane report, not a seventh acceptance lane and **never** updates
canonical class, member or field lineage.

## Local private run

Use a Python 3.11+ environment with the current exact SpawnPK-Client source.
Provide original SHA-pinned client JARs and an unused output path outside the
repository:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.v309_accepted_owner_cp_research `
    --v308-jar 'C:\path\to\original-v308.jar' `
    --v309-jar 'C:\path\to\original-v309.jar' `
    --out 'C:\path\outside-repo\v309-accepted-owner-cp.json'
```

The CLI fails closed on incorrect private JAR SHA, frontier-pinned report SHA,
incomplete or reassigned accepted anchors, classfile SHA mismatch, incomplete
archive manifests, existing output and parsing/semantic ambiguity. Never send
the source JARs, full method index or raw CP values to GitHub.

## Proof limits

- Only the 1,092 previously paired old/new classes with exact entry SHA
  verification may receive stable logical-ID class aliases.
- Only typed descriptor/CP class owners may be normalized. Raw string
  constants, CP tags, field/method names, numeric bits, branch operands,
  arbitrary unresolved third-party classes and the proposed class's own
  member identities retain their original strict comparison semantics.
- Every class in both original JARs is examined for the conservative
  >=3-method necessary coarse shape gate. A 1/1 pool is supporting evidence
  against alternate CP-matching owners, not an accepted class identity.
- No report contains private paths, method names, instructions, CP payloads,
  literal values, fingerprints, or decoded class definitions.

Original private research preflight (separate from hosted CI) found 3 unique
pairwise supported CP witnesses for `CLIENT_CLASS_000943` after normalizing
only preaccepted class owners, up from 1 with the existing self-only mapping.
Complete old/new coarse necessary pools were 1/1 across 10,472/10,502
classes, with 1,092 accepted entries hash-verified in both versions.
**This preflight alone does not certify the final merged module.**

Full explicit class-identity review remains required before any canonical
mapping acceptance. The existing recovery frontier must stay
`ACCEPTED_INCOMPLETE`: 143 unresolved fields, 26 descriptor-blocked,
zero newly accepted identities. Source M1 remains last measured at 98 javac
errors.
