# Generic historical lineage backfill

The generic historical backfill reuses the ordinary R3 matcher, member-identity
candidate generation, trusted lineage transfer, field-position proof and
authority-candidate finalization for a historical target build.

It is intentionally different from the v307 fixture-specific backfill.

## Trust boundary

The generic path adds **no historical exception** to R3. Exact and otherwise
trusted matcher relations are transferred. Ambiguous, unmatched or unresolved
classes and members remain unresolved and therefore block ordinary authority
promotion.

A result can therefore be useful while still returning exit code 3:

- exit 0: the ordinary authority candidate is complete;
- exit 3: the historical derivation is valid but blocked on unresolved review;
- exit 2: an exact authority/hash/schema/expectation precondition was refused.

## v305 -> v308 generalization target

The repository pins the reverse-matcher expectations for the known alternate
historical v305 fixture in
`fixtures/v305-v308-historical-reverse-match-summary.json`.

Because the backfill runs from canonical v308 authority **back to** v305, the
matcher orientation is:

- current/old side: v308, 1,129 classes;
- historical/new side: v305, 1,099 classes;
- matched: 1,074;
- exact SHA: 513;
- structural unique: 533;
- package anchor: 23;
- weighted mutual-best: 5;
- ambiguous: 10;
- current-only: 55;
- historical-only: 25.

This is expected to remain blocked until the historical review tail is
resolved. A blocked result is the correct outcome; it must not be converted
into canonical lineage by weakening matcher thresholds.

## Example

```powershell
spk-generic-historical-lineage-backfill `
  .\client-v308.jar `
  .\client-v305.jar `
  .\authority\v308-index.json `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  --current-build-id v308 `
  --historical-build-id v305 `
  --historical-build-number 305 `
  --expected-current-sha256 854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6 `
  --expected-historical-sha256 a9a5d1f35a6657b5c26939ca30e008748e718f6b206cc8fd93b64b57c4833385 `
  --expected-match-summary .\fixtures\v305-v308-historical-reverse-match-summary.json `
  --out-dir .\generated\v305-historical-lineage
```

Client JARs remain private and outside Git.
