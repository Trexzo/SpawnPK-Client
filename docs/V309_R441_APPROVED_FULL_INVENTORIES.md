# R441 — Approved whole-source and class-inventory SHA gate

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R440 draft PR #1236  
**Status:** DRAFT, UNMERGED, NOT DEPLOYED. Owner-private files and running client were not accessed.

## The remaining integrity issue

R440 checks the pinned recovered `LootHistoryStore.java` SHA and matching baseline `LootHistoryStore.class` SHA, and it requires the expected **1,277 Java sources / 1,394 classes**. However, the other **1,276 Java sources and 1,393 compiled classes** could have changed since their original R421 acceptance inventory while leaving the counts and Store-specific hashes unchanged. R425 previously compared each tree only to the snapshot captured at the **start of its own run**. That confirms a stable build input, not an independently reviewed pre-existing baseline.

R441 makes this a **mandatory fail-closed gate**, not an advisory diagnostic.

## Digest specification (v1)

`tools/r441/approved_full_inventory.py` computes two different domain-separated, deterministic inventory fingerprints. Each file is represented as a `[relative POSIX path, lowercase SHA256 of file bytes]` pair. The pairs are sorted by path, wrapped as `{"files":[...],"format":"SpawnPK-R441-approved-inventory-v1","kind":"java"}` or `kind:"class"`, serialized as canonical ASCII JSON (sorted object keys, compact separators), and SHA256-hashed. On Windows and Linux the same relative filenames and file bytes give identical digest values.

The two pins must be **approved independently of the candidate under test**. A hash calculated from the potentially altered current tree is an **observation**, not an approved baseline. These SHA values are not signatures or evidence of chain-of-custody by themselves.

## Enforced at three execution points

- **R440 read-only preflight:** New required CLI `--approved-source-inventory-sha256` and `--approved-class-inventory-sha256` inputs. After the original R421 Store source/class pins and counts, reject a mismatch anywhere in the complete source or compiled class trees. Rehash before and after the audit; no compile, client start, history access or generated candidate.
- **R425 private overlay compiler:** Require the same two pins independently in `validate_inputs`, and recheck the approved baseline snapshot in `verify_unchanged_build_inputs`. Existing exact class-delta and Store acceptance checks remain mandatory.
- **R432 cross-process gate:** Require the same two pins in `validate_owner_references`, verify the original full-tree digests before R422, then again after the separate JVM processes complete. The exact candidate `LootHistoryStore.class` SHA, 17 named tests, and 73+ Store assertions remain mandatory.
- **Owner PowerShell entrypoint:** Require `-ApprovedSourceInventorySha256` and `-ApprovedClassInventorySha256` in addition to R440's two dependency pins for both read-only `-AuditOnly` and explicitly opted-in R425/R432 execution. It forwards identical reference SHA values to all three processes; it never computes them and self-approves them during execution.
- Private-gate stdout failures are expressed as `R441_APPROVED_JAVA_INVENTORY_SHA_MISMATCH` or `R441_APPROVED_CLASS_INVENTORY_SHA_MISMATCH`, without printing filenames or private byte data.

## Obtaining the owner-approved references

Use a previously preserved, independently reviewed **R421 inventory or archive**, not the same files being tested in TEMP. The approval process should confirm the original snapshot's origin and timestamp, original source/class file lists and checksums, and tool version. Generate the two canonical hashes using `inventory_digest` on that *trusted snapshot's* path-to-file-SHA mapping. Keep that approved record **outside the client runtime and outside public GitHub**. Supplying freshly measured hashes from an unverified tree would defeat R441's assurance.

There is no previously approved full-inventory digest available in the public repository or this chat's execution environment. Therefore **real R441 preflight, R425 compile and R432 acceptance remain blocked** until the operator provides approved values. Do not replace them with guessed values or override the gate.

## Hosted evidence and safety

Sixteen new tests cover deterministic hashing, OS-independent ordering, source/class domain separation, same-file-count byte modifications and renames, missing reference pins, invalid paths/hashes, R440/R425/R432 mandatory comparisons, owner PowerShell argument forwarding and preserved no-release settings. The Windows/Ubuntu × Python 3.11/3.13 / JDK21 CI matrix also runs previous fabricated R440, R432, R426, and R439 suites. No private owner source or class is uploaded to hosted CI.

No R415/R417 retained deletion-intent marker, acknowledgment sidecar or persistent write fence is removed or weakened. R424 commit=false remains fixed. Real R427–R431 asynchronous deletion integration, actual owner-private 1,278-source compile and 1,399-class check, R425 39+ Store assertions, R432 73+ Store assertions / 17 JVM checks, live Swing/EDT responsiveness, shutdown/restart, and v312 runtime acceptance remain outstanding.

**No merge, JAR install, real loot-history deletion, journal cleanup or release is authorized.**
