# R372 — Non-destructive interrupted loadout-folder rename recovery

**Repo:** Trexzo/SpawnPK-Client; stacked on R371 draft PR #1164. **Private source release gate CLOSED. Draft and unmerged.** No real game or live cache was used.

## Reproduced source-level interruption issue

R371 writes a new folder file and its version marker, then commits the `order.settings` list, then deletes the previous folder. Process termination before the final delete leaves **both** saved files. The legacy `getFolderNames()` scanner automatically re-imports any unlisted filename, so an interrupted rename can appear as two folders after a restart even though only one is meant to be active.

## Private R372 behavior

- A bounded `R372V1` SHA-pinned rename intent is staged **before** writing the new folder. It records old/new folder names and the original raw SHA-256 of source data and `order.settings` (or `MISSING`).
- On folder discovery, the existing ordered list is authoritative: before order commit, suppress the *new* orphan from automatic UI discovery; after order commit, suppress the *old* orphan. **No startup auto-delete or rewriting** is performed. Both physical files are retained for manual recovery.
- A generic order write is refused while any rename receipt is unresolved. The active rename uses its own checked order-commit entry point.
- A post-commit finish step verifies original source checksum, readable destination and v5 marker, and committed order, then takes the original folder's cooperative lock before retiring it. It removes the receipt after successful retirement. Invalid old marker entries are checked before deleting old data.
- Source changes and malformed receipts cause fail-closed refusal. The GUI's inherited non-modal status callback reports save/rename failures, although actual Swing rendering has not been tested.
- If a new destination was never saved and both source and order still match their initial hashes, the uncommitted receipt can be discarded without touching data.

## Verified, private, offline

Full Java 11 target build with JDK21: **1,277 source files -> 1,387 classfiles** (the added nested intent class accounts for the extra class). Independent clean extraction and build produced candidate JAR SHA-256 `0ca478f292a371460502ba96f28efaeb17f2b572965e57ea0379b72b2bb2917b`.

**36 new** source-backed rename-recovery assertions, with **184 inherited** distinct checks: 44 store, 28 order settings, 29 version receipt, 60 serializer across UTF-8/ISO-8859-1, and 23 adjusted R371 rename tests. **220 checks total**. The inherited R371 fixture was updated to expect R372's earlier refusal when the order file is an unsafe directory, rather than expecting an orphan to be created.

Exactly **two of 1,277** private Java sources changed versus R371: `LoadoutFolders.java` and `LoadoutStore.java`. Public CI tests the synthetic SHA witness only; **it does not contain or execute private Java**.

## Important limitations

- This is a **non-destructive startup reconciliation**, not a single atomic transaction for both folder files, ordering and version markers.
- An ambiguous, malformed, or externally modified receipt requires operator inspection. No startup automatic disk deletion. The generic order writer is blocked while any receipt remains, including after a simulated interruption, until resolution.
- Cooperative locks cannot protect against uncooperative writers. There remains an external race at final validation/deletion and a race between an atomic receipt-file check and its creation.
- No power-loss fsync/directory durability, actual-client GUI, login/reconnect, original v309 binary parity, production v312 compatibility or real user-cache validation has been performed.

**DO NOT MERGE OR DEPLOY** without additional recovery, compatibility, runtime, concurrency and durability acceptance. The original v309 JAR, production v312/updater, caches and live services are unchanged.
