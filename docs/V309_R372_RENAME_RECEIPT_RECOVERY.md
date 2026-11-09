# R372 — interrupted loadout-folder rename receipt and conservative replay

**Repository:** `Trexzo/SpawnPK-Client` (stacked draft on R371 PR #1166).
**Owner-private baseline:** R371 SHA `d48a249c392993e088f8a404760c278ef74c566822d20e840bb51fdec4799d3a` — 1,277 reconstructed Java source files.
**Owner-private candidate:** R372 SHA `582bd22720fa6655b8082d83ec69f01f9073f1e79eb0ddf225eccab00d441e4b` — exactly two changed files:
`rs/gui/loadouts/LoadoutFolders.java` and `rs/gui/loadouts/io/LoadoutStore.java`.

## Source-backed finding

R371 uses copy-first folder rename: destination folder bytes and v5 marker are saved before deletion of the old data. This preserves the only good copy on a failed save, but a crash between copy and deletion leaves both folders. The original R371 code does not record whether the duplicate was intentionally created or is an interrupted rename. An actual-source offline fixture reproduced an R371 restart listing both old and new names.

**Do not auto-delete folders based only on matching content.** Two independent valid folders can contain the exact same serialized bytes.

## Private R372 bounded candidate

- Before destination copying, a new `.loadout_rename-<SHA-prefix>.pending` receipt records old/new names, the original raw SHA-256 and SHA-256 of the *expected serialized destination bytes*. It is written with `CREATE_NEW` and flushed at file level under two consistently ordered cooperative folder locks.
- The rename copies to the new folder using the existing R371 `saveFolderIfAbsent`; after a successful copy it validates the receipt and **both** raw hashes while holding both cooperative locks. Only then does it delete the old data, its known version/temp sidecars, and the receipt, and update the visible folder map. A failed copy never deletes the original.
- `getFolderNames()` conservatively replays pending receipts on restart: discard an uncommitted copy intent; finish a byte-exact committed copy; or refuse cleanup, report a status warning and retain both files for manual review when hashes or receipts disagree. Overlapping/malformed receipts never authorize deletion.
- The folder scanner accepts only regular, non-symlink files and deduplicates repeated *identical* `order.settings` entries. It never deduplicates distinct folder filenames merely because serialized contents happen to match.

## Verified privately (not by public GitHub Actions)

- **R371 failure snapshot reproduced:** after the destination commit and before deletion, both folder files appear on restart.
- **R372 actual-source Java contract:** **56/56 assertions**, including healthy rename, crash-before-copy, crash-after-copy, crash-after-old-deletion, changed source or destination, held source lock, malformed receipt, identical independent folders, repeated ordering entries, symlink/directory scanner exclusion and existing destination.
- **Inherited actual-source contract:** R371 rename **16**, store **44**, order.settings **28**, R370 version receipts **29**, R365 serializer **60** (two JVM charsets): all PASS.
- **Full private build:** OpenJDK21, `javac --release 11 -proc:none -g:none`, **1,277 Java sources → 1,388 classfiles**, exit 0. A fresh full source/dependency kit extraction built the byte-identical JAR SHA-256 `e876f097c8858438b3c421f3f94c5710af91e72217b31ed36c5a877cd25bb545`.
- Private source/archive/dependency attestations live in the separate private deliverable; this PR contains **only** a public fail-closed receipt verifier, SHA witness, **21 synthetic tests**, Windows/Ubuntu CI and this report.

## Hard limits (release gates remain closed)

R372 is not a transaction across folder bytes, `order.settings`, v5 markers and rename receipts. A crash before receipt persistence may still leave the prior state; a power loss may lose directory entries or reorder persisted writes. File `force(true)` is **not** proof of directory fsync or crash durability. Cooperative `FileLock` does not protect against older/unrelated writers; last check-to-delete windows can still race uncooperative writers. A malformed/untrusted receipt is reported and retained, not auto-repaired. Known legacy metadata sidecars are cleaned only when their types are safe. No real original-client GUI runtime, authenticated login, reconnection, true power loss, production v312 compatibility, or original-v309 JAR parity was tested.

**Source-M1 gate: CLOSED. Private Java source: NOT published. PR: DRAFT / UNMERGED.** No changes to owner cache, live server, signed updater, production v312 or original v309 JAR.
