# R430 — existing R415–R417 journal compatibility and read-only admission bridge

**Repository:** Trexzo/SpawnPK-Client  
**Stacked on:** R429 draft PR #1225  
**Status:** PUBLIC SYNTHETIC ONLY, DRAFT / UNMERGED. All owner-private release gates CLOSED.

## Source-based finding: R415's persistent deletion is intentionally single-shot

R430 reviewed the public, previously validated research documents and executables for R415, R416 and R417:

- `docs/V309_R415_NONCLOBBER_DELETE_INTENT.md`: the private R415 confirmed-delete writer stages/forces history and an immutable version-1 intent marker, publishes the marker by **no-clobber hard link** and then attempts R410's strict atomic history replacement. **On success it deliberately leaves the intent marker present and disables subsequent history writes.** Its earlier version performed confirmed persistent delete on Swing EDT.
- `docs/V309_R416_PASSIVE_RESTART_SCHEMA_VALIDATION.md`: an owner-private but dormant, read-only schema/digest validator can verify a committed image, but **does not adopt history or unblock writes**.
- `docs/V309_R417_RESTART_ACK_CRASH_MODEL.md` and `tools/r417/restart_ack_model.py`: the private R417 source added an ack/ack.tmp metadata-only **admission fence** ahead of the R414 intent classifier. A public *synthetic* ack publisher exists, but **there is no live private acknowledgment producer**. Even a valid-looking ack marker **does not authorize another write**. The public model returns `NONE`, `ABORTED_NO_ADOPTION`, `COMMITTED_UNACKED_FENCED`, `ACK_RECORDED_FENCED`, or `QUARANTINED` depending on the old/new digest, schema, and sidecar evidence.

Consequently, R427/R428's public `Store.commit` contract **cannot be wired to an always-ready durable delete adapter**. In the current private design, producing a confirmed persistent delete leaves its own intent evidence on disk and the admission fence intentionally blocks the next operation. A future integration must preserve this behavior and cannot turn an acknowledgment-looking file, R429's unrelated experimental ledger, or an in-memory `CONFIRMED` UI receipt into a write-unblock token.

## R430 code: no new protocol and no writes

### Read-only compatibility bridge

`tools/r430/inspect_existing_journal_readonly.py` calls the **existing**, public R417 classifier `tools.r417.restart_ack_model.inspect` rather than copying its parsing logic or creating yet another marker format.

It strictly accepts only an already-existing **`R430-Synthetic-*` directory directly under the Python TEMP root**. Parent directory symlinks, changed metadata, unexpected file types and unbounded inputs refuse. It double-classifies the evidence while comparing complete bounded pre/post metadata/digest snapshots of the canonical fabricated history, the R415 intent/intent.tmp, the R417 ack/ack.tmp, staging history, and the R429 **experimental** ledger name.

The bridge returns one of these **deny-only** statuses:

| Existing R417 observation | R430 interpretation | Writing/deletion/cleanup permitted? |
|---|---|---|
| `NONE` | `R430_NO_EVIDENCE_OWNER_LEASE_AND_STAGE_GATES_STILL_REQUIRED` | **No** |
| `ABORTED_NO_ADOPTION` | `R430_ABORTED_BEFORE_REPLACE_FENCED` | **No** |
| `COMMITTED_UNACKED_FENCED` | `R430_COMMITTED_UNACKED_FENCED` | **No** |
| `ACK_RECORDED_FENCED` | `R430_ACK_RECORDED_BUT_STILL_FENCED` | **No** |
| `QUARANTINED` | `R430_QUARANTINED` | **No** |
| Any classification with an R429 experimental ledger name present | `R430_EXPERIMENTAL_LEDGER_PRESENT_FENCED` | **No** |
| Input/snapshot/identity mismatch | `R430_REFUSED` | **No** |

The response explicitly sets `writer_authorized=false`, `delete_authorized=false`, `marker_cleanup_authorized=false`, `client_executed=false`, `private_source_inspected=false`. It never creates, deletes, renames, writes or acknowledges journal evidence. **`NONE` is not a green light:** authorization still requires the actual R419 owner lease, R411 stage gate, store epoch and an independently correct private writer adapter.

This uses the **invented public R417 schema model**. It is not a source-exact replacement for Gson canonicalization or the real R416 restart inspector. The pre/post snapshots are optimistic TOCTOU checks, not a defense against a hostile path replacement or non-cooperating writer.

### SHA-pinned owner-private source audit — not executed

`tools/r430/audit_private_existing_admission.py` is an **owner-opt-in, source-only** auditor for the exact previous R421 isolated source hash:

`LootHistoryStore.java` SHA-256 `0369e9b55e194ecfebfd754d15f66e6de84067634f16799a3c57c435b0616b29`.

It reuses the existing public R417 `verify_ack_guard()` structural checker to demand correct **ack and ack.tmp markers**, metadata-only `NOFOLLOW_LINKS`, **ack-sidecar inspection before R414 intent classification**, and no mutation APIs inside the ack guard. It separately requires R419 owner-lease symbols and the established load/save/clear method symbols. An unrecognized source, unexpected hash or changed guard **REFUSES**. Its success still explicitly states `runtime_integration_verified=false` and all write/delete/cleanup permissions false.

The private R421 owner source was **not accessible** in R430 because Desktop Commander remains monthly-quota paused. No actual private file was read, executed or compiled. The source audit has **only fabricated negative tests** in hosted CI.

## Public independent test coverage

- `tests/test_v309_r430_existing_protocol.py`: **26 fabricated TEMP protocol tests**: old image / committed image / valid ack (all fenced), ack orphan, changed nonce, intent/ack/history staging, corrupted marker, changed digest, noncanonical and invalid JSON, oversize file, symlink and dangling-sidecar evidence, extra R429 experimental ledger, changing evidence between inspections, two inconsistent classifications, independent CLI process output, denied non-synthetic roots, and exact byte preservation of synthetic history/sidecars.
- `tests/test_v309_r430_private_source_negative.py`: **12 invented source-auditor controls**: pinned SHA correctness, exact ack and ack.tmp names, nofollow guard, guard-before-intent ordering, no mutation APIs, required R419 owner methods, wrong filename/digest and read-only source bytes.
- `.github/workflows/v309-r430-readonly-bridge.yml`: dedicated **Windows and Ubuntu × Python3.11/3.13** CI. Final PR-head results must be verified independently.

All 38 tests operate only on invented text/JSON/sidecars; none exercise recovered Java/client classes, owner private history, the actual SpawnPK startup or full Swing plugin lifecycle. A passing hosted suite is not proof of physical crash safety.

## Next real-client integration blockers

1. Owner-PC access must resume before source-exact, private actual-class read-only acceptance can run. The corrected R422 private cross-process retest and R425/R426 1,278-source private overlay compilation remain incomplete.
2. Map the actual private `r411StageState`, `r414IntentState`, `r416InspectRestartCandidate`, R417 ack-sidecar checks, R419 writer-lease ownership and R415 `persistHistory()` confirmed-delete path under the same serialized owner gate. **Do not invent a new live ledger** or remove existing evidence.
3. Before wiring R427/R428 async controller into `LootTrackerPlugin`, make clear whether a confirmed disk write deliberately leaves the owner session quarantined. UI receipt and future disk-write admission are **different** statuses. The first private integration should be **passive read-only, no automatic recovery or history deletion**.
4. R429's research ledger is **not** a substitute for R415–R417, and a sidecar acknowledgment in the public model is not a trusted restart-adoption proof. Manual, authenticated recovery design and actual runtime testing remain separate milestones.
5. No automatic history migration, journal cleanup, forced shutdown/release, private source publication, game launch or v312 installation is authorized.

**Keep R430 draft/unmerged. Release gate CLOSED.**
