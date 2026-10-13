# R124 — client-only assets and cross-build source-reuse inventory

## Scope and authority

This lane exists **only** to reconstruct and eventually compile the original SpawnPK Java **client**. It does not incorporate independently authored server source or assert original-server identity.

The uploaded private `.spawnpk` archive was opened **read-only** with no execution of the contained client JARs, helper JAR, binaries or scripts.

| Original client | Embedded member | Independently verified SHA-256 | Java classfiles | `rs/` classfiles |
|---|---|---|---:|---:|
| v308 | `.spawnpk-data/client-v308.jar` | `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6` | 10,472 | 1,129 |
| v309 | `.spawnpk-data/client.jar` | `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38` | 10,502 | 1,159 |

## Actual v308 → v309 binary class delta

| Class area | Unchanged, same path | Modified, same path | New paths | Removed paths |
|---|---:|---:|---:|---:|
| Game client, `rs/` | **934** | 169 | 56 | 26 |
| Bundled dependency classfiles | **9,336** | 7 | 0 | 0 |

The v308 and v309 JARs contain 1,103 common `rs/` class paths, of which **934 are byte-identical**; this establishes a meaningful baseline for automated carry-forward. Unlike v307 → v308, however, the v308 → v309 update is **not a one-class change**. Renames and classfile-level churn require structural/semantic matching and member mapping; blindly copying identically *named* Java source into a new build is not enough. Unchanged binary classfile identity is a reusable proof, **not** final recompilation or runtime acceptance.

## Actual private runtime assets in uploaded archive

- **10,778** non-directory files under `.spawnpk/`, including **9,129** numerically named `raw/` resources and about **1,580** sprite files.
- Separate indexed asset data for the standard and OSRS caches (`main_file_cache.dat`, `main_file_osrs.dat` and `.idx*` files), additional `loc`, `obj`, `flo`, config, YAML and MIDI sources.
- **31** regular files under `.spawnpk-data/` aside from the two pinned client JARs (plus six directory entries) contain local runtime/profile/settings/log data and are categorically excluded from all public source releases and R124 report output.
- The ZIP also contains an auxiliary `AllInOneZipper.jar`, which is **not** trusted or executed.
- These assets support the offline client build/startup path, but the ZIP alone does not prove all dynamically fetched assets or resource loading behaviors are covered.

SHA-256 of the complete uploaded asset ZIP: `9de2ccf52a24455a1161fd8c215c3e6e7d14fdbbf65c8084538b043c20386b7f`.

## Future source-tree releases: one version per exact client build

Target structure, not a claim that source is already certified:

```text
recovered-source/
  v309/
    src/                       independently compiled deobfuscated original-client Java
    provenance/                exact binary and original→logical identity proofs
    SOURCE-MILESTONE.json      coverage, compiler and fallback criteria
    BUNDLE.json                reproducible class/resource compilation checks
  v310/
    src/                       standalone full next-build source snapshot
    provenance/
    SOURCE-MILESTONE.json
    BUNDLE.json
```

The initial target is a *full independently compilable v309 client* from the existing private source candidate (approximately 1,270 Java files), repaired against the exact-v309 original. The existing `recovered-source/README.md` publication gates remain authoritative; a decompiler dump is not a certified release.

**For each next update:**

1. Independently hash/index old and new exact JARs, including `rs/` classfiles, JVM methods/fields, resources and ABI.
2. Reuse accepted stable logical class/member IDs on unchanged bodies and exact proven structural identities; queue renamed or modified classes for graph/descriptor/callsite matching and human review.
3. Carry verified Java source and accepted semantic names forward into a **new versioned tree**, regenerate changed Java while preserving the prior source snapshot.
4. Compile the entire new source tree from Java sources only, with no original client JAR, precompiled project class or external fallback. Maintain necessary third-party dependencies separately with hashes.
5. Validate class-set completeness, verification metadata and independently mapped method behavior; test isolated startup/render/cache and network kill switches as distinct runtime gates.
6. Publish a new `recovered-source/vNNN/` only when existing Source Milestone and independent bundle gates allow it. This is different from original authorial Java-source identity or proving the entire live service backend.

Keep **runtime cache and assets external** to public Git. The build or launch configuration should accept an explicitly pinned local asset root; do not embed private logs, account data, usernames, credentials, production endpoints or cached user data in a source release.

## R124 tooling

`python -m spk_recovery.private_client_asset_build_delta_r124 PRIVATE_ASSET_ZIP NEW_PRIVATE_REPORT.json`

The CLI pins both exact original-JAR SHA-256 values, inspects Java-class and cache/resource ZIP entries without executing them, validates archive member paths/symlinks/duplicates and records class-delta counts, grouped asset count/bytes, a content-derived asset manifest hash, and the number of excluded local profile files. **No complete private class index, account identifiers or assets are emitted.** The report's `full_deobfuscated_source_tree_accepted` and `runtime_equivalence_proven` remain false regardless of the match counts.

The Java build target needs the correct compiler configuration and separate dependencies; v309 original-owner work currently uses Java9 classfile constraints, whereas the candidate multi-module decompiler workspace targets Java11. Do not mistake a successful Java11 build for exact original Java9 parity.
