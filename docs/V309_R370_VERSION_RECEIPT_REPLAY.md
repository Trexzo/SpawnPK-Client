# R370 — recoverable loadout version-marker receipt (owner-private candidate)

**Correct GitHub repository:** `Trexzo/SpawnPK-Client`, stacked on R369 PR #1162. **DRAFT / UNMERGED.** This public PR has only the SHA-pinned verifier, witness, 18 synthetic Python tests, and 4-way synthetic CI. The complete owner-private candidate, source-backed Java fixtures, and binary dependencies are supplied separately, not committed here.

## Why the change was necessary

The recovered R369 `LoadoutStore.saveFolderWithLock` atomically moves a version-5 data file into its destination **before** creating the `<folder>_ver_5` marker. A process termination between the two operations leaves modern bytes with the previous version-4 marker. `LoadoutVersion.refresh` then chooses a legacy decoder, so later reads can misinterpret the committed data. A source-backed isolated R369 fixture reproduced the split-marker state (`R369_BASELINE_SPLIT_VERSION_CONFIRMED`). This is **not** evidence that a real user's folder has been damaged.

## Private R370 candidate

Two of 1,277 Java source files changed: `rs/gui/loadouts/io/LoadoutStore.java` and `rs/gui/loadouts/io/LoadoutVersion.java`.

- While holding the existing cooperative per-folder file lock, a save stages a narrowly bounded, SHA-256-identified pending version receipt **before** the folder data atomic replacement. The receipt records the old/raw and staged/raw folder fingerprints, not game credentials or a full copy of the data.
- The writer rechecks the destination fingerprint **after** creating the receipt and immediately before the data rename. Successful completion creates/validates the version-5 marker and removes the receipt.
- On a subsequent load, `LoadoutVersion.refresh` attempts receipt replay **before** selecting its decoding version, under the same cooperative lock. If the bytes match the staged version, the version-5 marker is restored. If the bytes match the old version, the incomplete receipt is discarded without upgrading. If neither matches, recovery **refuses** and preserves the receipt and existing data.
- Invalid receipt layouts, non-regular/symlink markers, unsupported version suffixes, and contested locks refuse recovery. Newly created metadata is staged and the journal's bytes are forced before rename, but **directory synchronization is not proven**.
- The receipt file uses a dotted/underscored name excluded by the legacy folder-name scanner. An older client that ignores this receipt remains unsafe against a split marker.

## Verification on the *actual reconstructed private Java source*

| Check | Result |
|---|---|
| R369 split-marker state | Reproduced (version 4 selected despite committed v5 bytes) |
| R370 source-backed simulated interruptions | **29 assertions PASS** |
| Inherited R368 loadout-store fixtures | **44 PASS** |
| Inherited R369 order.settings fixtures | **28 PASS** |
| Inherited R365 serialization fixtures | **60 PASS** (UTF-8 and ISO-8859-1) |
| OpenJDK21 `javac --release 11` | **1,277 Java sources → 1,386 class files, PASS** |
| Deterministic JAR SHA-256 | `6ce02f6c567d22baf5403535537793a23c6028cf0683c0b7c0ca11e97fd01536` |
| Independent build-kit extraction, all tests and rebuild | PASS, same JAR hash |
| Public synthetic Python tests | **18 PASS** locally; hosted CI separately assessed |

The source archive SHA is `df72e08423b4eb4ac030e92e3cad4743c9c98465131220624ffda4553ab05eb0`; the private reproducible build-kit ZIP SHA is `1ae1510176aad8f874ac08a7f278f3e6af0e41d6809616c8e5c2333ca8957e78`. The public witness pins both changed private source hashes and the **unchanged previous R369** archive SHA, without publishing its source bytes.

## Explicit remaining limitations

1. **No atomic multi-file transaction** across folder data, version markers, and `order.settings`. R370 recovers a specific data/marker interruption window only.
2. No OS power-cut testing or `fsync`-verified parent-directory durability; advisory locks do not protect against older/uncooperative writers. The final fingerprint-check-to-rename race is still present.
3. No actual original-v309 game process, GUI acceptance, authenticated login, real cache test, v312 compatibility or original client-JAR bytecode equivalence.
4. Source names are inferred readable reconstructions, not certified original author source. The private source release gate is **CLOSED**; this is not release-ready code.

**Production v312, signed updater, original v309 JAR, live server, credentials, and user cache were not modified.**
