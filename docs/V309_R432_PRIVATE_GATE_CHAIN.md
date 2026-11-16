# R432 — owner-private R425 compile acceptance AND R422 cross-JVM gate

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R431 draft PR #1227  
**Status:** DRAFT / UNMERGED, release gate CLOSED. No original private code, installed v312 files, or real loot history changed.

## Why this is the next critical gate

R425/R426 prepared an owner-private, SHA-pinned compilation process for R424's isolated **inspection-only** legacy cleanup patch. It can verify one Java store instance on fabricated TEMP history. However, R422's older actual-class cross-process suite (competing JVM ownership, OS lock release/reacquisition, simulated JVM halt and restart, missing-leaf directory creation, preserved markers) was **not part of that automated R425 acceptance gate**. An isolated single-JVM PASS is insufficient to establish safe ownership when two clients start concurrently.

R432 makes these **two independent actual-private acceptance stages mandatory in one owner-only workflow**. Unlike R427–R431's synthetic designs, this is a concrete **future owner-private integration gate**, although access to the original owner-private source/classes is still blocked.

## New read-only gate tool

`tools/r432/chain_private_process_acceptance.py` is an opt-in, owner-local continuation called **after** a successful R425 compilation. It:

1. Demands a fresh direct **`R424-Private-Candidate-R425-*`** child of owner TEMP, with no symlinked paths or existing R432 receipt.
2. Validates **the exact original R421 source/class SHA256 pins**, the 1,277-source/1,394-class baseline, both dependency SHA256s and the expected legacy-cleanup public helper SHA.
3. Re-hashes **all original and candidate source/class files**, then verifies R425's final acceptance receipt: compile-success status, at least 39 actual-class TEMP assertions, exactly 1 modified existing private Java source + 1 added helper (1,277→1,278), exactly 1 modified existing class + 5 helper classes (1,394→1,399), and **all release/history/write flags false**.
4. Calculates the **actual rebuilt private Store.class SHA256** and invokes the existing `tools/r422/run_private_store_acceptance.py` with that exact SHA, the same compiled class directory and dependency JARs, and the existing public `R422ActualStoreAcceptance.java` harness.
5. Refuses anything short of the R422 suite's **17 distinct named cross-process checks** and **73 actual private-store assertions**, including lock conflict, release/reacquire, simulated JVM crash/reacquire, fresh directory and marker preservation, and refusal of a non-synthetic TEMP root. Requires the receipt to contain the exact compiled class SHA and `private_release_authorized=false`.
6. Re-hashes **every owner-original and candidate source/class file, both dependencies, and the R425 receipt** after all subprocesses have exited, rejecting any drift or stale class. Writes an **R432 success receipt** to the fresh private TEMP candidate *only after* both gates succeed. It never writes or deletes game history, builds a JAR, deploys, removes an intent/ack marker or authorizes merge/release.

The R422 subprocess creates **new, named fabricated TEMP directories only**, which it preserves for audit. Its tests deliberately call `Runtime.halt(77)` on a short-lived *synthetic acceptance JVM*, not on the real game process. Their original owner-private class remains outside GitHub CI.

## Owner PowerShell entrypoint strengthened

The previously prepared `tools/r425/owner_only_run_r425.ps1` now performs R432 automatically **after** a successful R425 stage:

- Explicit `-RunOwnerPrivateAcceptance` opt-in remains mandatory.
- The source/class inputs remain the known isolated R421 owner TEMP workspace.
- A unique fresh candidate TEMP output is generated.
- R425 compile and single-store acceptance must finish and leave its exact final receipt.
- R432 performs cross-JVM acceptance against **the same compiled candidate class bytes**, then requires its own `R432-Final-Private-CrossProcess-Receipt.json`.
- A failure from either stage stops the entrypoint. **The PowerShell entrypoint does not launch or modify the SpawnPK client and has no deployment step**, even after both receipts pass.

This entrypoint is **not executed in hosted CI**; no real recovered owner source/classes/dependencies are available there. The installed client stays unchanged.

## Public-hosted verification scope

`tests/test_v309_r432_gate_chain.py` contains 22 mock- and fabricated-byte tests:

- Exact R425 receipt and actual-class requirements.
- Exact R422 17-case/73-assertion process receipt and same-class SHA.
- Negative cases for missing/duplicated checks, unsafe authorization fields, release flags, non-synthetic candidate path, preexisting receipt and missing candidate.
- Complete **mocked** R425→R422 chain through the actual R432 Python `run()` logic with invented source/class byte inventories and a mock subprocess response.
- Refusal after a failed mock R422 process, drift in candidate class bytes, tampered R425 receipt, unchanged compiled Store or dependency mutation.

`tests/test_v309_r432_owner_entrypoint.py` adds 6 static Windows PowerShell safety checks for no-deployment and mandatory two-gate ordering. `.github/workflows/v309-r432-cross-process-chain.yml` runs **Windows/Ubuntu × Python 3.11/3.13**, 28 public-only tests per matrix job. Hosted CI tests **do not compile the private Java classes or run real R422 processes**, and cannot be used as evidence that the owner-private gate has passed.

## Still not completed, and why this is not a release

- Desktop Commander previously refused remote owner machine commands due to its monthly service quota, explicitly instructing not to retry/reconnect. **R432 was not executed on the owner's recovered source tree.**
- R424's source transformation is not yet applied to the real private classes. The actual 1,278-source compile, 1,399-class comparison, R425 39-assertion and corrected R422 73-assertion/17-check tests are **still pending real owner-machine execution**.
- R427–R431 are independently authored public prototypes: **the actual asynchronous confirmed-delete Store adapter and LootTrackerPlugin Swing callbacks remain unchanged**.
- The R415–R417 persistent write fences and R419 owner lease cannot be bypassed by a new journal, in-memory successful UI receipt, or the R429 research ledger. Persisted quarantine and actual shutdown-save ordering are not production-verified.
- After passing actual owner-private compilation and cross-process tests, **full plugin startup/shutdown, actual EDT responsiveness/latency, restart with unresolved sidecars, and v312 compatibility still require separate acceptance**.
- No live history migration, automatic intent cleanup, forced lock release, user-profile access, JAR install or release is authorized.

**Keep R432 draft/unmerged and production release gate CLOSED.**
