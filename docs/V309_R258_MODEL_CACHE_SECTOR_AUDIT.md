# R258 — independent offline model-cache sector audit

Read-only audit of actual isolated archived cache `main_file_cache.dat` + `main_file_cache.idx1` staged for R249/R257. Extracted the 34 unique model IDs observed in R257 `R257_MODEL_MISSING` logs.

**Verified 34/34 model IDs have structurally readable index and data-sector chains, zero missing/corrupt**. Validation matches `IndexStore.readFile()`: six-byte index entry, 520-byte sectors, 512-byte payloads, model ID and chunk sequence, linked next pointer. Important: type-0 models read from `getIndexes()[1]` / file `idx1`, but the sector header indexNumber is **2** because constructor uses `var5 + 1`. Each audited model was fingerprinted by SHA256; no game assets or originals published.

Source request/delivery chain established:
1. `Model.method1145(id)`: if in-memory header null, `field199.requestModel(id)`.
2. `CacheLoader.requestModel` queues `type=0`; `processLoadQueue` reads `getIndexes()[type+1].readFile(id)`, sends success to `completedQueue` or failure to `missingQueue`.
3. `Client.s()` calls `pollCompletedRequest()`, and for type 0 invokes `Model.method1700(data,id,revision==1)` to insert model header.

**Acceptance boundary:** offline archive presence does not establish that runtime requests were dequeued, decompressed, delivered or parsed successfully. R257 sampled 40 missing-header observations (34 unique) and an object-readiness scene gate -3. R258 did not rerun the graphical client, prove model header installation, render terrain or run Windows. No production Java changed.

Private reproducible evidence `SpawnPK_R258_Model_Cache_Integrity_Audit.zip` SHA256 `25a87f07f1bb29c4ca5797afb1023c8bd4d08fd62419a0c2eecfabb6f8233f12`. Next isolate **per-model** queue transitions and header population for representative IDs without bypassing `areObjectsWalkable()`. Keep PR #1084 DRAFT.