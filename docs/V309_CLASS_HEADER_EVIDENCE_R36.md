# R36 — exact JVM class-header evidence

R25/R31 validate instructions and verification frames, R32 inventories methods,
and R35 separately inventories declared fields. The JVM class header is also
important for proving that a reconstructed Java class matches an original.

The shared `spk_recovery.bytecode_profile` parser now preserves these
properties of an original or recompiled class:

- `class_access` — exact JVM class access and modifier bitmask
- `super_name` — direct JVM superclass identity (null for Object)
- `interfaces` — ordered direct interface declarations
- `classfile_major`, `classfile_minor` — exact JVM classfile version

`spk_recovery.class_header_evidence.compare_class_headers` returns a
**research-only** evidence object with a distinct check for each of these
properties. Invalid or missing observations are rejected; owner names must
be identical on both inputs and no cross-build alias is inferred.
Output contains aggregate Boolean checks, not raw JVM member coordinates.

The independent `javac --release 8/9` test fixtures demonstrate that
changing only superclass, interface list, class-final modifier or JVM major
version changes the corresponding evidence without altering method names.

These observations do **not** establish semantic equivalence or accepted
class lineage. Future class-wide parity work can incorporate this evidence
alongside exact JVM fields, methods and StackMapTable, but **never**
automatically promote canonical mappings from name or shape similarity.

No SpawnPK binaries, decompiled Java or original private class paths are
included in the repository or in hosted tests.
