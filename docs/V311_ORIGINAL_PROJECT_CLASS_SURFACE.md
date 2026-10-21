# v311 original-client project-class surface (2026-10-21)

This is **real read-only evidence from the original uploaded v311 client JAR**, not a decompile, source release, byte-identical rebuild, or game launch. No JAR, cache, Java source, embedded literals, server addresses, or credentials are committed.

## Exact original authority

- Private input: `client(20261021-111920).jar`
- SHA-256: `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`
- ZIP entries: **10,947**, of which **10,527** are JVM class entries and **1,184** are under `rs/`; no duplicate ZIP member names, direct traversal entries or CRC errors were seen.
- All **1,184** original `rs/*.class` members have classfile major version **53** (Java 9 bytecode). This is a bytecode target, **not** a claim that building the recovered source needs no later JDK.
- Sum of uncompressed project-class entries: **3,709,911 bytes**.
- SHA-256 of the canonical sorted `rs/` project-class path/digest rows: `c9a88342e8f1d3eed57d113d0691b8ffb0014c46947637437705e03159e4d535`.

Each digest row is UTF-8 bytes `class-entry-path + NUL + lowercase SHA256(uncompressed class entry) + LF`; rows are sorted by complete ZIP member path. This fingerprint uniquely attests to the observed **content + location** of the project-class entries. It is not a cross-version class identity or semantic-name witness. `src/spk_recovery/indexer.py:project_class_surface` reproduces this from a fully parsed recovery index and explicitly rejects unparsed classes or inconsistent internal names.

## Actual observed distribution

| ZIP package prefix under `rs/` | Class entries |
|---|---:|
| `n/` | 173 |
| `l/` | 171 |
| `plugins/` | 155 |
| `gui/` | 106 |
| `ui/` | 91 |
| `o/` | 53 |
| Classes directly under `rs/` | 51 |
| `runelite/` | 44 |
| `r/` | 37 |
| `d/` | 36 |
| `k/` | 35 |
| `cache/` | 29 |

These are **obfuscated package labels**, not a source-workload estimate or proof of functional ownership.

## Critical source-recovery boundaries

- `rs/f/a.class` exists, class SHA-256 `01f0546471ba05b71cf4ceb8245f76fde9c3306375db41ef21323c8885d0281e`; original `ConstantValue` build 311 was independently inspected previously.
- `rs/Client.class` exists, SHA-256 `f37d249f40eb212086d334777dc5e9e707276a7cf129f6a00955071b5d9bda98`, uncompressed length **290,805** bytes.
- `rs/gui/Launcher.class` exists, SHA-256 `6b8eaea0b78fbb60e1d6e92497f6a5f8ab25a297e72d49889980fd224c1d9d27`.
- `rs/cache/osrs/util/OsrsMapDependencyScanner.class` exists, SHA-256 `fee0729269f73923a073cbfd658ac26c66b0d7db46446992e3428451385d317a`.
- `rs/eventbus/EventBus.class` exists, SHA-256 `7bcd16369a679f743b644bdf62c4b39dc50608ccbdbfe4768d142a7fc7af8259`.
- **`rs/Scene.class` and `rs/s/e/c.class` do not occur under those names in this v311 ZIP.** This does *not* prove scene logic was removed. They might have been renamed, repackaged, replaced or otherwise absent. Only cross-build class/method evidence can establish relationships.

## How this moves recovery forward

1. **Keep** v308 rebuilt Java regression evidence and the original v309 authority on their original versions. v311 is a distinct original-client release.
2. **Obtain an independently SHA-verified complete v309 or v310 original index/JAR**, and run the existing `spk-recovery update-intake` / `update-migrate` pipeline to v311. v309’s earlier original SHA authority is `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`; use that only for the actual original version, not the R308 privately rebuilt class-only JAR.
3. Transfer Java source/class semantic identities **only for exact/uniquely structurally proved matches**. Queue ambiguous, modified and unmatched classes. Focus initial human review on the scene/viewport family, `Client` and changed GUI/cache paths **after** matcher results confirm identity.
4. Only then produce a complete independent `recovered-source/v311/src/**/*.java` snapshot and apply the existing zero-fallback clean Java source build/provenance gates. No historical Windows Cooking ZIPs are prerequisites to these source-recovery tasks.

**Unresolved as of this observation:** no actual verified v309/v310-to-v311 class delta, no proof of class identity for absent old paths, no v311 complete source rebuild, and no native owner gameplay test. Do not infer any of these from the project-class fingerprint.
