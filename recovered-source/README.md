# Recovered SpawnPK client source

## Client-only, standalone per-build releases


## v311 intake and source migration boundary

The official client JAR received on 2026-10-21 has SHA-256
`5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`.
Its actual `rs/f/a.class` has a `ConstantValue: int 311` build field.
The immutable original file is **not** included here. The public
`authority/v311.json` contains aggregate evidence only; it is not a class
lineage, accepted deobfuscated source tree, game patch or release.

For a real v311 source milestone, use the **existing** R3A–R3F tools described in
`docs/UPDATE_INTAKE.md` and `docs/UPDATE_ORCHESTRATION.md`.
First generate/verify an exact prior-build index from the actual v310 or
v309 JAR (never label an index with a different build). Then run
`spk-recovery update-intake` from that index to the exact v311 JAR in a
**private workspace**. Where v310 is unavailable, a direct v309-to-v311
comparison is allowed but must explicitly say that it spans two builds;
no invented v310 delta. Do not infer changed/added/removed classes merely
from total JAR entry counts.

Transfer only exact-byte or proven unique-structural class identities;
hold ambiguous/new/changed identities for review and independently validate
members. Finish with a full standalone
`recovered-source/v311/src/**/*.java` snapshot that passes the existing
zero-fallback Java compile and release-verification gates. Old graphical
acceptance packages for the historical R308 rebuild are not mandatory
prerequisites to this *source recovery* work.

The objective is a genuinely **source-compilable original SpawnPK client** with deobfuscated class/member identities and separate local runtime assets. The **current official client is v311** (exact binary authority in [`authority/v311.json`](../authority/v311.json)); the full-tree recovered-source target must therefore be **v311** for new development. The prior v308 recovered-client rebuild and v309 Source-M1 work remain **historical/in-progress baselines**, not proof of a source-compilable v311 release. Existing old-build evidence must be preserved under its original version, and publication order is determined by verified source milestones, **not** by chronological build number.

Every accepted release is a **complete snapshot** in `recovered-source/vNNN/src/`, not merely a patch against the previous one. A subsequent release may reuse proven unchanged Java sources and stable semantic identities from the prior certified tree, but it must independently meet the new exact client binary's full class/source build gates. The versioned provenance records cross-build reused identities and the changed/renamed-class queue.

Client runtime caches (`.spawnpk/`), original `client.jar` files, and local profile/log/settings data (`.spawnpk-data/`) remain strictly outside Git. Asset manifests may be hash-pinned privately; no independently implemented server tree is part of these client releases.


This directory is the canonical in-repository home for verified recovered Java source releases.

Publication is versioned by exact client build:

```text
recovered-source/
  v308/
    SOURCE-MILESTONE.json
    BUNDLE.json
    src/**/*.java
    provenance/
      SOURCE-PROVENANCE.json
      *.json
  v309/
    ...
  v311/
    ...
```

A version directory is not ordinary generated output. It may be populated only from a Source Milestone publication bundle that has passed all exact-authority, semantic/fallback, clean-compile, zero-project-binary-fallback, exact class-set, source-tree and independent bundle-verification gates.

For build 308, the canonical Java tree will be:

`recovered-source/v308/src/`

Until the v308 milestone is publishable, that version directory intentionally does not exist.

Raw decompiler workspaces, client JARs, classfiles and private recovery inputs remain outside Git.

The canonical publication repository is `Trexzo/SpawnPK-Client`; no separate source repository is used.
