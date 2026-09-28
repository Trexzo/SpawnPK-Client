# Exact local closure acceptance

GitHub-hosted jobs in the private staging repository can fail before step 1,
so exact private acceptance must also be reproducible on a trusted local
machine without weakening any recovery gate.

These wrappers do not commit, upload or print private recovery payloads. They
only compose existing fail-closed recovery CLIs against private local paths.

## R8DEP38 / issue #92

Run scripts/Invoke-R8DEP38ExactLocalAcceptance.ps1 with the exact v308 client,
the complete private R8DEP37 authority set, the exact readable/bundled JAR,
all exact official dependency artifacts, and an empty private output directory.

The wrapper requires a clean checkout exactly equal to origin/main, exact v308
SHA-256 854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6,
and exact readable/bundled SHA-256
e12e4f917ba2c48ea306e3b4d4cc19c58c5e23cd4f5c33f4ae339ea6fce53c99.

It rebuilds the private substitution plan, applies R8DEP38, independently
verifies the runtime postimage, and accepts only a manifest with verified=true.

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
6. run current-main recovered-workspace release orchestration with the exact
   generated private collision plan;
7. verify the release including private collision-plan provenance;
8. build and independently verify the Source M1 authority artifact;
9. build and reproduce the Source Milestone manifest;
10. build and independently verify the source-only publication bundle.

If current-main clean rebuild is still blocked, the wrapper stops before any
publication step and prints the new compiler frontier from clean-rebuild.json,
including the deterministic javac frontier ID when available. That new exact
frontier, rather than the older 1,288-error R8N measurement, becomes the only
valid input for any further source-repair decision.

A PASS is emitted only after the milestone reports publishable=true and the
publication bundle verifies. The verified local publication bundle remains
private until a separate publication decision is made.
