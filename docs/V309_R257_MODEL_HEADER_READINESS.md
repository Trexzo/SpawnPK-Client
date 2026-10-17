# R257 — Model-header readiness is the next scene gate

Canonical source: `rs/io_.java` `areObjectsWalkable()` iterates objects parsed from landscape bytes and calls `ObjectDefinition.method1531()`. ObjectDefinition checks each model ID via `Model.method1145()`. That method returns false and calls `CacheLoader.requestModel(id)` when a model header is absent.

Executed a **diagnostic-only** `Model.java` overlay, independently compiled using `javac --release 11` against the R256 full source-built classfiles. Replayed real client in Linux/Xvfb against the same localhost login and region 249→73(400,400)→81 sequence. Logging was capped at 40 occurrences.

**Runtime evidence:** 40 missing-model observations representing **34 distinct model IDs**; example IDs 1124, 1139, 1517, 1405, 1406, 1407, 1409, 2259. R256 diagnostic continues to show initial four terrain and four landscape files missing, then both counters zero while `tryEnableDetailedGraphics()` returns -3 objects-unwalkable (pending request count 392 at observed sample). The test did not observe scene promotion to graphicsMode 2. There is **no proof yet that requested models never resolve**: captured diagnostics are sampled, and the environment closes its localhost listener.

Private evidence ZIP SHA256 `ee423b0970b704a17c9286e7a7080805a8bf1d77fdc8098dbcac8eae3facfe28`. Contains instrumentation, logs, screenshot and redacted test, no credentials. No canonical production source changed; native Windows and playable-world acceptance pending.

**Next:** inspect `CacheLoader.requestModel` queue completion, whether model IDs are present in the archived cache, and the timing of `Model` header insertion. Keep PR #1084 draft.