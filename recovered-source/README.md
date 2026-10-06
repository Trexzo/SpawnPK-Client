# Recovered SpawnPK client source

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
