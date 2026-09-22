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

These structural-role rules do not depend on decompiler line numbers or raw variable
spellings.

## Deliberate exclusions

This stage does **not** propose names for:

- ordinary locals;
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
