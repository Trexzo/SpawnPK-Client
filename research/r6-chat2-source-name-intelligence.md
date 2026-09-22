# Chat 2 R6 — conservative source-name intelligence

R6A inventories source parameters/locals with stable `SRC_*` identities. R6B provides the
non-canonical review boundary, and R6C owns explicit acceptance plus AST rewriting.

Chat 2's role is candidate production only.

## Initial producer

`source_name_intelligence.py` currently emits only high-confidence **parameter** proposals
when the parameter is tied to a canonical method whose semantic name is already
`ACCEPTED`.

Initial rules:

1. accepted `addFriend(long)`, `removeFriend(long)`, `addIgnore(long)`,
   `removeIgnore(long)`
   - single parameter -> `nameKey`
   - confidence `0.97`

2. accepted single-parameter setter `setX(T)`
   - parameter -> lower-camel `x`
   - confidence `0.93`

The producer refuses to use `CANDIDATE` method semantics as source-name authority.

3. R6A `catch` variables
   - declared type ending in `Exception` -> `exception`
   - declared type ending in `Error` -> `error`
   - `Throwable` -> `throwable`
   - confidence `0.92-0.94`

4. R6A try-with-resources variables
   - informative declared resource type -> lower-camel type role
   - e.g. `BufferedReader` -> `bufferedReader`
   - confidence `0.88`

5. R6A enhanced-for variables
   - informative element class type -> lower-camel element role
   - e.g. `Player` -> `player`
   - confidence `0.86`
   - primitive/wrapper/`String` element types are excluded

6. R6A ordinary locals with a unique informative class type in the method
   - e.g. exactly one local `Player` -> `player`
   - confidence `0.82`
   - duplicate same-type locals are left unresolved
   - arrays, generics, primitives, wrappers, `String` and `Object` are excluded
   - proposed name must not collide with another current source symbol in the method

These structural-role rules do not depend on decompiler line numbers or raw variable
spellings.

## Deliberate exclusions

This stage does **not** propose names for:

- ambiguous or duplicate-type ordinary locals;
- lambda parameters;
- parameters in methods without an accepted semantic method name;
- multi-parameter methods without a dedicated rule.

Those require stronger flow/context evidence.

## Output

The output is already in R6B's canonical input format:

```text
source_name_candidate_set
  inventory_id
  source_tree_sha256
  candidates[]
```

The tests pass the generated set directly through
`resolve_source_name_candidates()`, proving the producer fits the core review boundary
without any adapter or alternate schema.

No source name is accepted or rewritten by Chat 2.


## R6E carry-forward-aware diagnostics

Core R6E now owns accepted inferred-name carry-forward across regeneration and supported
cross-build updates. Chat 2 does not duplicate that transfer engine.

`build_source_name_carryforward_diagnostics()` consumes the canonical
`source_name_carryforward_report` and the current non-canonical candidate set to classify
research state only.

Candidate states:

- `new_candidate` — current Chat 2 inference has no R6E transfer relation;
- `candidate_same_as_prior_accepted` — current inference agrees with the previously
  accepted inferred name carried by R6E;
- `candidate_changed` — current inference disagrees with the R6E-carried accepted name.

R6E blockers are grouped separately as:

- `candidate_blocked_by_source_shape_drift`;
- `candidate_blocked_by_method_lineage_drift`;
- `ambiguous_after_regeneration`;
- `blocked_requires_review`.

This output remains diagnostic and non-canonical. It does not transfer a name, rebuild
R6E proof, accept a proposal, or authorize AST rewriting.

R7A also means a release-ready authority chain may include accepted rewritten source.
Chat 2 diagnostics are evidence feeding review; they are not release authority and are not
added to the R7A release manifest.


## R7C future-update boundary

R7C now carries an exact future client through R3 migration, authority promotion, accepted
class/member semantic carry-forward, and the R7 release path. It explicitly keeps R6
parameter/local inferred-name carry-forward as a post-source extension.

That means Chat 2 source-name diagnostics must not become a gate for exact binary,
class/member authority, or R7C release orchestration. They begin only after the new recovered
source inventory exists, consume R6E results when available, and return candidate/review
evidence rather than promotion authority.


## R7D reproducibility boundary

R7D independently verifies that an R7 release can be reproduced from its pinned authority
documents and optional on-disk artifacts/toolchain. That verification strengthens provenance
and reproducibility only. It does not upgrade an inferred parameter/local name into recovered
original source text, and Chat 2 must not use an R7D PASS as semantic-name acceptance evidence
beyond the evidence that originally justified the candidate or accepted inferred replacement.
