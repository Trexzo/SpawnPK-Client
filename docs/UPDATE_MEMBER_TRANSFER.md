# R3C verified member-lineage transfer

R3B establishes trusted class identity in the new build. R3C then consumes a
research `member_identity_candidates` document and appends only independently
verified member identities to canonical member lineage.

The research producer can be Chat 2 or a future automated intelligence tool.
Core does not import the research implementation.

## Auto-transfer policy

Current automatic member strategies:

- `stable_symbol`
- `structural_unique`

Anything else remains unresolved/review-only, including usage-context inference.

This policy is intentionally stricter than the research matcher. New inference
strategies can be promoted later only after core validates their evidence model.

## Verification before append

For every candidate relationship, core re-verifies:

1. candidate old/new SHA-256 against the supplied exact indexes;
2. both builds exist in canonical class lineage;
3. old owner and new owner resolve to the same stable `CLIENT_CLASS_XXXXXX`;
4. the old member coordinate already owns exactly one canonical
   `CLIENT_FIELD_XXXXXX` or `CLIENT_METHOD_XXXXXX`;
5. the old declaration exists exactly in the old index;
6. the proposed new declaration exists exactly in the new index;
7. access metadata agrees when supplied;
8. one new member coordinate cannot be assigned twice.

A successful relation is appended to the existing stable member record. Therefore
an already accepted semantic name naturally survives the client update without being
re-inferred.

## Command

```powershell
spk-recovery update-transfer-members `
  .\generated\v309.lineage.json `
  .\generated\v308.members.json `
  .\evidence\indexes\v308.json `
  .\generated\v309-intake\new-index.json `
  .\generated\v309.member-candidates.json `
  --old-build-id v308 `
  --new-build-id v309 `
  --out .\generated\v309.members.json `
  --summary-out .\generated\v309.member-transfer.json
```

## Unresolved policy

Unsupported strategies, unmatched members and skipped class pairs are retained in the
member lineage `unresolved` array. R3C never creates a new member ID automatically.

A later explicit promotion/review stage may decide whether an unmatched target member is
genuinely new.


## Field-specific trust hardening

Field names are not reliable cross-build identity anchors once same-shape fields are
inserted or reordered. Exact matched-method access-position research found concrete
cases where a surviving obfuscated field spelling pointed at the wrong logical field.

Core automatic transfer therefore distinguishes methods from fields.

### Methods

The existing trusted member strategies remain eligible:

- `stable_symbol`
- `structural_unique`

Owner-class identity and exact old/new declarations are still independently re-verified.

### Fields

Automatic transfer is allowed only when one of these stronger conditions holds:

1. the enclosing class relationship is `exact_sha256` and the field relationship is
   `stable_symbol`; identical class bytes make the carried declaration identity safe; or
2. the field relationship strategy is
   `exact_matched_method_access_positions`, proving the mapping through unique exact
   field-access positions inside already-correlated methods.

A `stable_symbol` or `structural_unique` field relationship inside a changed class is
retained as `member_identity_review` instead of entering canonical member lineage.

This is intentionally fail-closed. Reduced automatic field coverage is preferable to
silently carrying one incorrect field ID into semantic naming, remapping, or a later
authority snapshot.
