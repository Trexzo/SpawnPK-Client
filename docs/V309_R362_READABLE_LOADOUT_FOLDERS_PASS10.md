# R362 — v309 readable loadout folders, pass 10

**Repository:** Trexzo/SpawnPK-Client, stacked on draft R361 PR #1154. The Source-M1 release gate stays CLOSED. No private recovered Java source or dependency binaries are committed.

## Exact baseline and rename safety

Input: owner-private R361 full 1,277-Java-source ZIP, SHA-256 5905feaac54d8d449dbdb92cd3ce941d23e28e5e25c5033ea428d33d47bc3fe7. All 1,277 individual Java SHA-256 hashes are checked against the private archive manifest, and the two declaring class SHA values and exact source-wide token-reference counts are pinned by the public R362 JSON witness.

The Java-aware lexer skips comments and quoted literals; the source transform rejects unexpected source files, reference drift, naming collisions and malformed input. Applying the reverse transformation restores all 1,277 original R361 source files byte-for-byte.

## Ten source-grounded inferred names

| Original | Readable candidate | Source-observed purpose |
| --- | --- | --- |
| field3277 | ownerLoadoutsPanel | Owning LoadoutsPanel for UI and store calls |
| field3278 | selectedFolderName | Folder key returned by getSelectedFolder |
| field3279 | selectedLoadout | Selected Loadout returned by getSelectedLoadout |
| field3315 | allowedFolderNameCharacters | Array of allowed letters, numbers, punctuation and space |
| method1237 | setSelectedFolderAndLoadout | Updates selected folder/loadout, synchronizes equipment |
| method1043 | createLoadoutInFolder | Adds named Loadout after duplicate-name check |
| method2787 | saveFolderWithOrder | Saves folder data and order |
| method2390 | saveCurrentFolder | Persists selected folder when non-null |
| method1632 | syncEquipmentSelection | Sets selected Loadout on equipment panel |
| method2087 | validateNewFolderName | Checks empty, duplicates and allowed characters |

Four fields and six methods renamed; 81 Java identifier changes in six source files. The names are inferred descriptive candidates, not recovered original-author identifiers. No behavior or serialization format is intentionally changed.

Further semantic audit needed: some earlier readable names are misleading. The existing saveLoadout method deletes a loadout, and moveFolder swaps entries rather than moving an entire folder. R362 leaves both behaviors untouched.

## Owner-private independent rebuild

- OpenJDK 21.0.12.1; javac --release 11 -proc:none -g:none.
- 1,277 Java source files compiled successfully into 1,386 classfiles.
- Both dependency JARs contain zero compiled rs/ game-class fallback.
- Candidate source-built JAR SHA-256: 6cc712d0d7e5474e85b2f235c20f195620d49479a0a75225137f0c4cb3000440.
- A fresh extraction of the R362 build kit independently recompiled all 1,277 Java files and produced the exact same JAR SHA.
- Private R362 source ZIP SHA-256: f7b3d76a747b99accf33e8088eccfb5d32c7018ab25473d7430fe3f7190f6183.
- Private R362 reproducible build-kit SHA-256: 0869a04015a7487a9e80f34aa4ace01a982f681a6736394afc52bf2c40a4892f.
- Hosted GitHub CI uses synthetic sources only, not private source or original game.

Preparation with the public tool (offline owner-private environment): python scripts/prepare_v309_r362_readable_loadout_folders.py --r361-private-source R361-Readable-Source.zip --witness research/v309-source-recovery/r362-loadout-folder-readability-witness.json --new-private-output R362-Readable-Source.zip

## Limits and safety

Build success and reversible names are NOT proof of original-v309 binary or JVM-descriptor parity, reflection/serialization compatibility, authenticated login, game-world use, reconnect or production readiness. The original v309 JAR, live v312 client, signed updater, original caches and server are untouched. Keep this PR draft/unmerged; do not publicly upload proprietary reconstructed source or binaries.
