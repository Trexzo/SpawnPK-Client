# Architecture

## Principle

The exact obfuscated client is evidence. It is never the editable source of truth.
The persistent source of truth is a versioned semantic mapping plus machine-generated
indexes/fingerprints and explicit provenance.

## Layers

1. **Authority** — immutable SHA/build facts for each known exact client.
2. **Indexer** — whole-JAR hashes, class metadata, constants and structural fingerprints.
3. **Version matcher** — exact equality first, structural identity second, semantic matching later.
4. **Mapping DB** — stable logical identities and human names independent of ProGuard output names.
5. **Remapper/repackager** — whole-JAR symbol/resource rewrite with verification.
6. **Decompiler** — generated readable source view after namespace remapping.
7. **Source recovery** — selectively promoted, buildable Java when useful.

## Non-goals

- Claiming original developer names when the stripped JAR cannot prove them.
- Committing proprietary client binaries.
- Treating generated decompiler output as authoritative source.
- Re-running deep semantic analysis for every unchanged class on every release.
