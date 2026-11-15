# R425 — owner-private R424 overlay compilation and actual-store acceptance gate

**Repository:** Trexzo/SpawnPK-Client
**Parent:** R424 draft PR #1220
**Status:** DRAFT / UNMERGED. Live client and release gates CLOSED.

## What R425 adds

R424 produced a SHA-pinned, owner-only source overlay preparation tool. It could stage a private Java source copy containing a no-follow legacy cleanup helper with deletion **hard-coded OFF**, but there was no repeatable process to compile it, inspect all resulting class bytes or test its behavior using the real reconstructed `LootHistoryStore`.

R425 adds a deterministic **owner-only source → class → actual-store acceptance runner**:

`tools/r425/compile_and_accept_private_overlay.py`

The runner has **not** been executed on the actual R421 owner-private source. Desktop Commander is online but the service explicitly reports that this month's usage quota is exhausted and instructs not to retry or reconnect. R425 did not bypass that limit.

## Required owner-private inputs

When owner device access resumes, use the isolated R421 source and class directories only:

`%TEMP%/SpawnPK-R386-Isolated-Acceptance/R421-Private-NoFollow-Cache-Directory-Preflight/Source-Candidate-R421/source`

`%TEMP%/SpawnPK-R386-Isolated-Acceptance/R421-Private-NoFollow-Cache-Directory-Preflight/R421-Compiled-Classes`

Alongside the two preexisting isolated dependency JARs `R239_filtered.jar` and `R218.jar`, each with its actual SHA-256 explicitly supplied to the runner. Use the installed **JDK21** `javac.exe` and `java.exe`; the runner compiles with `--release 11`.

The private original sources/classes are **never uploaded**. The runner must receive the public companion `tests/fixtures/r424/LootLegacyCleanupR424.java` and public owner-only acceptance harness `tests/fixtures/r425/R425ActualPrivateOverlayAcceptance.java` as local files.

For output supply a fresh direct child of TEMP, named `R424-Private-Candidate-R425-*`. No existing output path may be overwritten, no production folder is accepted, and existing private files remain unchanged. The R424 patcher first verifies its exact original source SHA and expected old method/caller structure, then copies the isolated tree.

## Admission and exact-byte gates

Before running the compiler, R425 independently checks:

- R421 `LootHistoryStore.java` raw SHA256 exactly `0369e9b55e194ecfebfd754d15f66e6de84067634f16799a3c57c435b0616b29`.
- R421 compiled `LootHistoryStore.class` SHA256 exactly `65272371272fdcf9142095880a042aa007a9a088f93c969a57878188fae37a09`.
- 1,277 original Java sources and 1,394 original class files with no symlinked input files.
- Both dependency JARs are regular files and have exactly the supplied SHA256.
- Source/class roots belong to the named isolated R421 TEMP acceptance workspace.
- The R424 source overlay has exactly **one modified existing source** `LootHistoryStore.java` and **one added helper source** `LootLegacyCleanupR424.java`, yielding **1,278 Java source files**.
- Full JDK21 `javac --release 11` compilation must pass.
- The compiled class delta versus R421 must contain **exactly one changed existing class** (`LootHistoryStore.class`) and **exactly five new helper classes** (`LootLegacyCleanupR424.class`, `$1`, `$Entry`, `$Receipt`, and `$Status`); **no removed or unrelated changed classes**. Expected total **1,399 class files**. These are predicted exact checks, **not yet verified private compile results**.
- The input private store source and class SHA256 must remain unchanged after acceptance.

Any mismatch, compile failure, crash, timeout or missing receipt refuses the gate. The runner preserves local compiler and harness logs for review, without uploading private Java source or output.

## Actual reconstructed-store TEMP acceptance, owner only

`tests/fixtures/r425/R425ActualPrivateOverlayAcceptance.java` exercises the rebuilt private class against a freshly created `R425-Synthetic-*` direct child of TEMP. It checks:

- The new `r419DeleteStaleLeased()` startup integration leaves a synthetic retired tree, nested records, seen-keys file and canonical history intact, including across repeated calls.
- Unleased and released store sessions cannot delete synthetic legacy paths.
- Five categories of fake unresolved stage/intent/ack evidence remain intact and refuse deletion.
- When supported, a symlink to an outside synthetic sentinel remains untraversed; no outside file is modified.
- The test never constructs `LootTrackerPlugin`, starts the game, opens user loot records, acknowledges real deletion markers or enables cleanup.

**No real owner-private R425 acceptance execution has taken place.** Passing these checks is a prerequisite, not proof of the full Swing plugin lifecycle, EDT responsiveness or live game stability. The R422 real private multiprocess retest also remains pending.

## Public-only tests (not recovered-client acceptance)

GitHub contains an independent *public synthetic* Store stub inherited from R422; R425's tests inject a fabricated `deleteStale()` method into a temporary copy of that mock, compile it with the public R424 helper and the R425 owner harness, then execute it on synthetic TEMP paths.

- `tests/test_v309_r425_compiler_gates.py` — 18 invented source/class inventory and SHA admission positives/negatives, checking unrelated changes, missing helper classes, wrong counts or pins and absent owner inputs.
- `tests/test_v309_r425_public_harness.py` — 13 fabricated Java 11 harness/process and safety checks.
- `.github/workflows/v309-r425-private-overlay.yml` — Windows/Ubuntu × Python 3.11/3.13 with JDK21, **public-only**, with no recovered private Java/class files in the workflow.

The suite must be verified on final branch head before claiming hosted success. These mock tests verify the **test machinery** and boundary conditions, not the actual private integration.

## Remaining release blockers

1. Desktop Commander quota still blocks any owner-private compilation, hash audit and actual-class R425 acceptance. No attempt to bypass the usage pause.
2. The R424 patcher still needs **actual** SHA/structural acceptance on the isolated R421 source; there may be unknown source shape differences that force refusal. A successful fabricated-source patch does not prove real transformation.
3. Even successful isolated actual-class acceptance would leave the full `LootTrackerPlugin` startup/restore/shutdown thread interleaving, cross-process contention, rapid restart, Swing EDT-blocking confirmed deletes and power-loss recovery unverified.
4. R415–R417 journal evidence remains quarantined. No automatic reconciliation, deletion receipt cleanup, history data migration or permission to unblock writes.
5. Non-cooperating processes, live lock-path replacement and hostile symlink ancestor swaps are outside the existing no-follow cooperative model.

**Keep R425 draft/unmerged and the private release gate CLOSED.** No actual game, installed v312, player history, JAR, credentials or other live application data was modified.
