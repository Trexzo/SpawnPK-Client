# R2C2 Main validation — exact-v308 semantic seed acceptance

Date: 2026-09-22

This records Main/Core validation of the reviewed Chat 2 semantic seed against a freshly
indexed exact-v308 authority. It does not commit generated lineages, transformed JARs,
decompiled source, cache data, or any private client binary.

## Exact authority

- client SHA-256: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`
- indexed entries: 10,970
- parsed classes: 10,472
- `rs/**` classes: 1,129
- parse errors: 0

Fresh canonical baseline generation produced:

- 1,129 `CLIENT_CLASS_*` identities, 0 unresolved
- 7,247 `CLIENT_FIELD_*` identities
- 6,564 non-constructor `CLIENT_METHOD_*` identities
- 13,811 total member identities, 0 unresolved

## R2C2 exact resolution

The committed candidate set was resolved again against those freshly generated exact-v308
lineages.

Result:

```text
review_id   SEMREVIEW_DD69CD752A6E46181BAC
proposals   39
unresolved  0
```

The newly generated review object was object-for-object equal to the committed
`v308.semantic-review.chat2.r2.json`.

The explicit acceptance spec selects all 39 reviewed proposals:

- 32 class semantics
- 3 field semantics
- 4 method semantics

No proposal ID is inferred from confidence alone; the acceptance is bound to the exact
deterministic review ID.

## R4A/R4B validation before canonical acceptance

Main simulated the full 39-proposal acceptance locally before persisting the acceptance
decision.

R4A produced:

```text
classes accepted/remapped: 32 / 32
fields accepted/remapped:   3 / 3
methods accepted/remapped:  4 / 4
```

Class remap risk scan found:

- 0 exact class-name literal hits
- 0 package-resource hits
- 2 service-descriptor entries, neither targeting the mapped SpawnPK classes
- manifest review remained explicit as designed

The first R4B run stopped correctly at the member-safety boundary. The seven member
renames produced five high, one medium and one low scanner risk. High findings were driven
by public-API exposure and conservative one-character string/reflection hits.

For validation only, Main created a report-ID-bound local safety acceptance after reviewing
those exact findings. That acceptance was not committed.

The resulting whole-JAR ASM rewrite and independent transformed-JAR verification passed:

```text
source SHA-256:
854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6

readable JAR SHA-256:
912e17b2bffb2a9ef24d13f58ff788966f297cf4f1cc641add6f71d2b2149ffc

verification_pass:
true
```

This proves the accepted semantic seed is internally materializable as a verified derived
readable JAR. It does not prove external binary compatibility for renamed public members.

## Coverage effect

Before acceptance:

```text
classes  0 / 1129
fields   0 / 7247
methods  0 / 6564
overall  0 / 14940
```

After the 39-proposal acceptance:

```text
classes  32 / 1129 = 2.8344%
fields    3 / 7247 = 0.0414%
methods   4 / 6564 = 0.0609%
overall  39 /14940 = 0.2610%
```

The project therefore still has substantial semantic recovery work remaining.

## Remaining release boundary

R4C and later source/rebuild stages were not executed in this validation because no
hash-pinned CFR/Vineflower decompiler JAR was available in the local evidence set.

No unpinned decompiler was substituted.

Member-safety acceptance also remains a separate review-bound artifact and is deliberately
not made canonical by this semantic acceptance change.
