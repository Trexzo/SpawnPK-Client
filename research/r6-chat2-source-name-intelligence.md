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


## R6G direct accepted-field flow evidence

R6A deliberately inventories source declarations, not data flow. Chat 2 now adds a separate
non-canonical AST evidence layer rather than changing the canonical R6A inventory schema.

The R6G scanner only records exact assignments shaped like:

```java
this.acceptedField = sourceSymbol;
```

A binding is usable only when all of these hold:

- the source tree SHA exactly matches the R6A inventory;
- the source method matches the R6A source-method identity;
- `this.<field>` resolves by name to exactly one **ACCEPTED** canonical field semantic on
  the same canonical owner;
- the RHS is a plain identifier resolving to exactly one R6A `parameter` or ordinary
  `local` in that source method;
- one source symbol maps to only one accepted field semantic;
- one accepted field in one source method is not claimed by multiple source symbols;
- the proposed field-derived name does not collide with an existing sibling source symbol;
- Java reserved identifiers remain rejected by the existing candidate safety gate.

The flow layer intentionally ignores:

- `other.field = value`;
- casts, ternaries, method calls or transformed RHS expressions;
- anonymous-class bodies, where plain `this` has a different owner;
- lambda parameters;
- unaccepted or ambiguous fields;
- stale source trees or mismatched inventories.

### Candidate behavior

An unambiguous direct assignment contributes a source-name candidate at confidence `0.96`.

If an existing accepted-method semantic candidate proposes the same name, R6G corroborates
it and adds the direct-field evidence.

If accepted method semantics and accepted field flow propose different names for the same
source symbol, Chat 2 emits **no candidate** for that symbol. Diagnostics record the
semantic disagreement instead of choosing one authority over the other.

This allows conservative naming of multi-parameter constructors/setters and duplicate-type
parameter/local cases that type-only inference cannot safely resolve, while preserving R6B
review and R6C explicit acceptance as the only promotion path.


## R6H direct accepted-field local aliases

R6H extends the same non-canonical AST flow layer to direct ordinary-local aliases:

```java
Player var1 = this.primaryPlayer;
Player var2 = this.secondaryPlayer;
```

This solves a class of cases that the type-only rule must intentionally leave unresolved:
multiple ordinary locals can have the same informative type while still having distinct roles.

The alias rule is stricter than general initializer inference:

- the initializer must be exactly `this.<field>`;
- the field must have ACCEPTED canonical semantics on the same canonical owner;
- the source symbol must be an ordinary R6A `local`;
- the local is matched by exact R6A declaration position, current spelling and source-method
  identity, not merely by type or line number;
- casts, method calls, ternaries, other receivers and transformed expressions are ignored;
- one source symbol mapping to multiple accepted fields is ambiguous;
- one accepted field mapping to multiple source symbols in one method is ambiguous;
- local/nested class scope is tracked so an enclosing method context cannot leak into another
  class body;
- anonymous-class bodies remain excluded because plain `this` has a different owner there.

A direct field-to-local alias contributes confidence `0.94`. A direct symbol-to-field
assignment remains `0.96`. If multiple valid relations corroborate the same field semantic,
the candidate keeps the stronger confidence while retaining all provenance.

As before, disagreement with another accepted-semantic source-name rule causes Chat 2 to
withhold the candidate rather than choose a winner.
