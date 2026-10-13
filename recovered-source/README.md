# Recovered SpawnPK client source

## Client-only, standalone per-build releases

The objective is a genuinely **source-compilable original SpawnPK client** with deobfuscated class/member identities and separate local runtime assets. The current active first full-tree target is **v309**. v308 remains an exact historical reference and may also receive a certified standalone source release; publication order is determined by verified source milestones, **not** by chronological build number.

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
```

A version directory is not ordinary generated output. It may be populated only from a Source Milestone publication bundle that has passed all exact-authority, semantic/fallback, clean-compile, zero-project-binary-fallback, exact class-set, source-tree and independent bundle-verification gates.

For build 308, the canonical Java tree will be:

`recovered-source/v308/src/`

Until the v308 milestone is publishable, that version directory intentionally does not exist.

Raw decompiler workspaces, client JARs, classfiles and private recovery inputs remain outside Git.

The canonical publication repository is `Trexzo/SpawnPK-Client`; no separate source repository is used.
