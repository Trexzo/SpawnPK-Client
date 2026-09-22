# Update pipeline

Every new client build follows the same deterministic process:

1. Hash and index the entire JAR.
2. Compare entry hashes against the previous authority.
3. Transfer mappings for byte-identical classes.
4. Transfer mappings for uniquely structural-matched classes even if ProGuard renamed them.
5. Deep-analyse only modified/new/ambiguous logical classes and methods.
6. Rebuild the global call/reference/resource graph and validate the full mapping.
7. Produce an update report and candidate mapping revision.
8. Repackage/remap only after validation passes.

A full semantic re-audit is triggered when structural match confidence collapses,
obfuscation characteristics materially change, or a major client architecture change is detected.
