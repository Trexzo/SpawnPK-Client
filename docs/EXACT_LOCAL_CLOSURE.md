# Exact local closure acceptance

GitHub-hosted jobs in the private staging repository can fail before step 1,
so exact private acceptance must also be reproducible on a trusted local
machine without weakening any recovery gate.

These wrappers do not commit, upload or print private recovery payloads. They
compose the existing fail-closed recovery CLIs against private local paths.

## R8DEP38 / issue #92

The R8DEP wrapper no longer requires a preserved R8DEP11-R8DEP37 private
manifest chain. It rebuilds the dependency authority locally from the smallest
stable exact inputs:

- exact v308 client JAR, used for the canonical SHA preflight;
- exact readable/bundled client JAR;
- the complete exact official dependency artifact set;
- an empty private output directory.

The wrapper requires a clean checkout exactly equal to origin/main, exact v308
SHA-256 854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6,
and exact readable/bundled SHA-256
e12e4f917ba2c48ea306e3b4d4cc19c58c5e23cd4f5c33f4ae339ea6fce53c99.

It then regenerates, in order:

1. DEPREF project-to-dependency reference authority;
2. DEPREMAP structural class/member proof;
3. DEPRETAIN exact residual/source-retention classification;
4. private DEPREPLACE replacement authority;
5. R8DEP24 runtime frontier;
6. R8DEP25 static runtime closure;
7. R8DEP26 resource equivalence;
8. the current combined R8DEP27/R8DEP28 dynamic-call and literal-target proof;
9. R8DEP29 dynamic target classification;
10. R8DEP30 augmented closure;
11. R8DEP31 dynamic-only structural mapping;
12. R8DEP32 dynamic member/API transport;
13. R8DEP33 additive replacement extension;
14. R8DEP34 extended closure;
15. R8DEP35 extended resource equivalence;
16. R8DEP36 substitution readiness.

If readiness is false, the wrapper emits SPK_R8DEP_EXACT_LOCAL_BLOCKED and
prints the exact blocker counts for class closure, remaining mappings, dynamic
targets, ServiceLoader provider discovery, resources and native requirements.
It stops before any runtime mutation.

Only when R8DEP36 reports runtime_dependency_substitution_ready=true does it
build the private R8DEP37 substitution plan, apply R8DEP38, independently
verify the postimage and require verified=true before emitting PASS.

This means an exact local run can now either close the stale evidence gap or
produce the precise current blocker frontier without depending on private
GitHub Actions.

## Source Milestone 1 / issue #168

The Source M1 wrapper no longer assumes that an exact-v308 R8S/R8T collision
workspace has already been preserved. It rebuilds that authority from scratch
on the trusted local machine.

Required private/local inputs are:

- exact v308 client JAR;
- exact v308 source index;
- current canonical class lineage;
- current canonical member lineage;
- exact member-safety acceptance bound to the readable build;
- pinned Procyon 0.6.0 JAR;
- an empty private output directory.

Optional source-rewrite acceptance can be supplied for the additional release
verification check.

The wrapper requires a clean checkout exactly equal to origin/main and verifies
both exact v308 and Procyon SHA-256 pins. It then runs this fail-closed chain:

1. rebuild the exact readable-client authority;
2. derive a private identifier-bearing namespace collision plan;
3. require that the plan eliminates all collision edges;
4. transform the readable JAR and independently require zero post-transform
   collision edges;
5. decompile only project classes from that transformed JAR with pinned
   Procyon, binding the collision transform into the recovered workspace;
   on Windows the wrapper first marks the empty top-level Source M1 output
   directory as per-directory NTFS case-sensitive with one elevated fsutil
   call, so Procyon resolver/source staging and later clean-javac release
   staging inherit the same case-sensitive transport before Python/JVM gates
   independently verify and consume those paths;
6. run current-main recovered-workspace release orchestration with the exact
   generated private collision plan;
7. verify the release including private collision-plan provenance;
8. build and independently verify the Source M1 authority artifact;
9. build and reproduce the Source Milestone manifest;
10. build and independently verify the source-only publication bundle.

Source normalization is also allowed to repair a JVM-legal but Java-source
ambiguous nested-type static-field spelling when exact bytecode proves the
access. For example, if Procyon emits `pkg.Outer.Inner.FIELD` but the
enclosing-class hierarchy exposes a visible field named `Inner`, javac can
bind `Inner` as a value instead of the nested type. The normalizer may force
that owner through type context as `((pkg.Outer.Inner)null).FIELD` only when
the nested class, static field, visible shadow and exact per-method
getstatic/putstatic access counts all agree.

If current-main clean rebuild is still blocked, the wrapper stops before any
publication step and prints the new compiler frontier from clean-rebuild.json,
including the deterministic javac frontier ID when available. The same
authoritative run also writes a private identifier-bearing javac diagnostic
report beside release-run.json; that private artifact must never be committed.
That new exact frontier, rather than the older 1,288-error R8N measurement,
becomes the only valid input for any further source-repair decision.

A PASS is emitted only after the milestone reports publishable=true and the
publication bundle verifies. The verified local publication bundle remains
private until a separate publication decision is made.
