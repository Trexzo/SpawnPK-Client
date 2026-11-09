# R371 — copy-first loadout folder rename (private candidate)

**Repository:** `Trexzo/SpawnPK-Client` · stacked on R370 PR #1163 · **DRAFT/UNMERGED**.

## Actual R370-source defect

`LoadoutFolders.renameFolder` updated the in-memory folder map, deleted the old on-disk data, and **only then** called the unchecked `LoadoutStore.saveFolder` for the new name. If a second client held the destination's cooperative lock, or if a destination file existed on disk but was missing from the panel model, the save could fail **after the only expected old folder data was deleted**. In the isolated genuine R370 Java-source test, the locked-destination rename ended with `NoSuchFileException` reading the old folder. This does not establish that any user's real cache was damaged.

## R371 owner-private Java candidate

Exactly two recovered Java files changed from R370:

- `rs/gui/loadouts/io/LoadoutStore.java`: preserves the original void `saveFolder(String,List<Loadout>)` API, adds `saveFolderChecked` and a rename-only `saveFolderIfAbsent`. The checked result is successful **only after** the data save, version-5 marker and receipt cleanup complete. A destination that already exists is refused under the existing cooperative destination lock; the existing optimistic raw-file fingerprint checks remain.
- `rs/gui/loadouts/LoadoutFolders.java`: save a new destination **before** deleting the old file or changing folder selection and menu state. If the checked save refuses, old bytes, current folder selection and the in-memory map remain unchanged. A successful copy is followed by old-file cleanup and the existing atomic `order.settings` writer.

No new on-disk serialization format. No production client replacement or live user-cache write.

## Offline evidence

- R370 private source ZIP SHA-256 `df72e08423b4eb4ac030e92e3cad4743c9c98465131220624ffda4553ab05eb0`; R371 private source ZIP SHA-256 `d48a249c392993e088f8a404760c278ef74c566822d20e840bb51fdec4799d3a`.
- Source manifest and static witness independently confirm that **only two of 1,277 Java files changed**.
- Owner-private JDK21 `javac --release 11`: **1,277 sources → 1,386 compiled classes**. Two independent builds of the same source create JAR SHA-256 `3c9ced189d6f2ecc27ed6e3b7a49ce83f08abd4ca88820b8ab414c37ea407434`.
- Genuine-source offline rename fixture: **16 assertions passed** on R371 across held destination lock, existing unexpected destination on disk, and healthy rename with readable new data and version marker. **R370 baseline failed the held-lock preservation assertion** because the old file was already gone.
- Inherited original-source offline contracts: **44 store + 28 order settings + 29 version receipt + 60 serializer assertions passed**.
- Public CI contains **18 synthetic-only verifier tests** under Windows/Ubuntu Python 3.11/3.13; it does not build or execute proprietary Java source.

## Remaining risks / release gates

This is a **copy-first rename**, not a transaction spanning old file deletion, new file, version markers, and `order.settings`. If old cleanup fails after a successful copy, both names may remain; crash recovery and ordering reconciliation are not proven. Cooperative locks do not prevent unrelated/legacy writers, and a last fingerprint-check-to-rename window persists. Power-loss durability, real GUI behavior, original-v309 binary parity, login/reconnect, and v312 compatibility **NOT TESTED**. Private source release and production promotion remain **CLOSED**; keep this PR **DRAFT, UNMERGED**.
