# R8DEP30 augmented runtime closure audit

R8DEP30 asks whether proven dynamic class targets can safely extend the exact
R8DEP25 static dependency closure.

The important boundary is that R8DEP11 `DEPREPLACE` was built from the
project-referenced dependency surface. A bundled class discovered only through
a dynamic literal may therefore have no accepted replacement authority.

R8DEP30 never fills that gap by structural similarity.

For every proven dynamic class or service-class target it reports one of the
following root outcomes:

- already present in the static R8DEP25 closure;
- authorized dynamic root because exact DEPREPLACE already classifies the
  bundled owner as `official_replaceable`;
- `dynamic_mapping_authority_gap` for a bundled target with no DEPREPLACE row;
- protected/non-traversable for residual, project-retained, project, platform,
  malformed, or otherwise non-authorized targets.

Only authorized dynamic roots are traversed. Traversal reuses the exact
constant-pool and descriptor reference extraction from R8DEP25 and continues
only through accepted `official_replaceable` owners. Residual,
project-retained, project-owned, and unclassified bundled owners stop the walk.

Official targets are reverified against the same Java-release-aware official
artifact authority.

Resource and native dynamic targets never become class roots. Their requirement
counts are carried forward explicitly.

A result with zero added authorized roots is valid and useful: it demonstrates
that the current remaining blocker is mapping authority, not closure traversal.

The report always keeps `runtime_capsule_mutation_ready=false`.
