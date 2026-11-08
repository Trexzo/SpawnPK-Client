# R366 — damaged loadout-file preservation candidate (private Java source)

**Repository:** `Trexzo/SpawnPK-Client` · stacked on **R365 PR #1158**. The recovered 1,277-file Java tree and both binary dependencies are **private**; this public PR contains only verification tooling, SHA witnesses, synthetic tests, and this document.

## Reproduced defect in original R365 candidate

`rs.gui.loadouts.io.LoadoutStore.loadFolder(folder, false)` calls `LoadoutSerializer.read` and catches an incomplete final record as `EOFException`, returning the valid prefix accumulated before the failure. A subsequent `saveFolder` opens the existing target with `FileOutputStream`, truncating it before serializing the shorter visible list. This can erase the damaged tail, preventing later recovery.

A source-backed, isolated Java fixture using the **actual private R365** `LoadoutStore`, `LoadoutSerializer`, `LoadoutVersion`, `Loadout`, and `LoadoutList` reproduces `CORRUPTED_ORIGINAL_WAS_OVERWRITTEN`. No live game, account, user cache, or network was accessed. UI/environment dependencies were replaced with synthetic fixture classes.

## R366 private candidate

Changes **only** `rs/gui/loadouts/io/LoadoutStore.java`:

1. Before replacing an existing folder file, re-read the entire file into a temporary `LoadoutList` using the current serializer and matching version markers. Reject overwrite if it cannot be parsed completely. The original file remains present and unchanged; existing in-memory loadout-prefix behavior is not expanded or promoted as recovery proof.
2. Serialize into a unique same-directory temporary file and close it before replacing the destination. Use `Files.move` with `ATOMIC_MOVE` and `REPLACE_EXISTING`; **fail closed without a non-atomic fallback** when atomic replacement is unsupported. Clean up the temporary file on failure.
3. Only after the move succeeds, write the v5 marker and remove older markers. Maintain existing v5 record ordering and avoid changes to the data format.

This reduces overwrite hazards but is **not yet an end-to-end recovery solution**. The UI currently lacks a distinct read-only/corruption notification and a guided repair action. The version marker update is not one transaction with the data-file rename. The code does not prove fsync/power-loss durability and does not handle an external writer racing between validation and replacement. Such risks must be assessed before release.

## Private source-backed verification

JDK21 `javac --release 11` compiled **1,277 Java files into 1,386 classfiles**. Two full builds of the candidate produced identical JAR SHA256 `8466751415455ba22fad9feb822fb8f086e2d294386ea62ef6a56ebe2500fa38`. The separate source-backed harness passed **23 checks** covering healthy writes, damaged trailing header preservation, invalid stored lengths, failed-write temporary cleanup and valid legacy v1–v4 migration to v5. Its R365 baseline failed at the expected damaged-original-overwrite assertion.

Private R365 source ZIP SHA: `671a627540009372ea2af45d19c239fce7953c34fe3a613372570715d069ac98`.

Private R366 source ZIP SHA: `107110c74a57e6feaa5d7fd72a13e386c36c13bd354191fbe305704fd59cc1b3`.

Exact modified source SHA values and complete source-archive pins are in `research/v309-source-recovery/r366-loadout-store-preservation-witness.json`. The verifier checks both archives, all source manifests, **exactly one changed owner**, and explicit *NOT_TESTED* release flags.

## Public CI / remaining gates

Public CI consists of **14 synthetic verifier regression tests** on Windows/Ubuntu and Python 3.11/3.13. It does not compile or run private Java and therefore cannot substitute for the isolated private source-backed test.

**NOT TESTED:** untouched original v309 JAR parity, in-game loadout recovery, v312 compatibility, concurrent-writer races, power-loss/crash consistency, actual user cache files, authenticated login, reconnect. Keep the entire stack **DRAFT, UNMERGED**. Do not modify the original JAR, active v312, updater, caches, or network. **Private-source release gate CLOSED.**
