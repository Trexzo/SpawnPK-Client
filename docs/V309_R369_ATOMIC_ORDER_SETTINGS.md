# R369 — loadout `order.settings` atomic persistence, private candidate

**Correct repository:** `Trexzo/SpawnPK-Client`, stacked on R368 PR #1161. R368 remains draft and unmerged; R369 is also draft and unmerged. **No changes** to the live v312 installation, updater, original v309 JAR, owner cache or any game servers.

## Source-grounded issue reproduced

In the genuine SHA-pinned private R368 Java source, `LoadoutStore.writeFolderOrderSettings()` used a `FileWriter` directly on the destination. The file is opened for truncation before iteration of the folder names succeeds; an exception may leave the previous order lost. A genuine R368-source fixture produced **`R369_BASELINE_TRUNCATED_ORDER_SETTINGS`**. The R369 candidate preserves the original on the same fixture.

R368 already has atomic replacement and cooperative per-folder locks for individual loadout files, but `order.settings` remained a separate unguarded write. R369 changes **only** `rs/gui/loadouts/io/LoadoutStore.java`, one of the 1,277 recovered Java sources.

## Private candidate

- Write the folder order to a unique same-directory `.loadout_order_stage-*.pending` file and close the writer before `Files.move(... ATOMIC_MOVE, REPLACE_EXISTING)`. No non-atomic fallback.
- Hold a persistent `.loadout_order_lock.lck` with `FileChannel.tryLock`, refusing a second lock-aware writer instead of overwriting its work. The underscore keeps the lock out of the old folder-name scanner.
- Fingerprint the original bytes, then compare again immediately before commit. Refuse an unsafe nonregular or symlink target, or a file created, removed, or modified while staging.
- Preserve the default charset behavior of the original `FileWriter`/`FileReader` pair; R369 does **not** introduce a new folder-order format or alter serializer records.
- Report save refusal through R368's existing `reportLoadoutSaveFailure` callback, tested only with a lightweight panel stub (not a real GUI screenshot).

## Actual private validation, not GitHub CI

The owner-private R368 source archive SHA-256 `b1ff1d06068c6b09ab921a25784dfd6b4fafcb855775a7ed4a1cc6dcc89c9945` was compared against the R369 candidate archive SHA-256 `b5e2f1fc4a9b52d50c9fde3608ac8fef6b211805a96ca58b61b6ccc45e6c4502`. Both contain 1,277 source files with individually verified SHA-256 values. **Exactly one owner source changed**; the `r369-order-settings-witness.json` records the two owner hashes and expected JAR hash.

JDK21 `javac --release 11` compiled **1,277 Java sources → 1,386 classes**, three builds including an independently extracted private build kit producing the same JAR SHA-256 `bb118af9a7f131e76fc3d4a8f9dda5cb0d0ec8cfa6b20923cd564096c83dc268`.

The private source-backed fixture recorded **44/44 existing store checks**, **28/28 R369 order-file checks**, the separate no-truncation assertion, and **60/60 existing R365 serializer checks across UTF-8 and ISO-8859-1**. R369 covers in-process and second-JVM lock contention, invalid staged data, target creation/removal, same-length external mutation, temp cleanup, nonregular/symlink target refusal, and recovery after a refused save. Synthetic public verifier tests are different from these real-source-backed tests.

Run private source verification without running the game:

```sh
python scripts/verify_v309_r369_order_settings.py \
  --r368-private-source /private/R368-Readable-Source.zip \
  --r369-private-source /private/R369-Readable-Source.zip \
  --witness research/v309-source-recovery/r369-order-settings-witness.json
```

## Critical limits

This is **not** a transaction spanning folder-file bytes, `order.settings` and `_ver_5` marker files. It does not roll back in-memory folder changes after a save refusal, and its locks are cooperative: older clients and outside processes can ignore them. A change in the final hash-check-to-rename window can still race. A successful atomic rename is not proof of crash durability (`fsync` directory and full transaction journal not demonstrated). Actual original-game GUI rendering, authenticated login, same-process reconnect, live cache behavior, original-v309 binary parity and v312 compatibility were **not tested**.

Public GitHub contains only synthetic tests, integrity tooling, this report and bounded SHA witness—**no private reconstructed Java source or dependency binaries**. Source-M1 release gate **CLOSED**; **DRAFT / UNMERGED**.
