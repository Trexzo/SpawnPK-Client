# R261 — per-invocation object readiness, real Java client replay

Continuation of R260 using diagnostic-only `rs/io_.java` overlay. Removed shared time-window failure ID accumulators: each `areObjectsWalkable(regionX, landscapeBytes, regionY)` invocation now has local failing object IDs, local count, and a call sequence number. Exactly one overlay Java class compiled successfully with `javac --release 11` against the existing R256 source-built classes. **Canonical R247 Java was not modified.**

Executed isolated Linux/Xvfb real client against authenticated-test localhost framing (synthetic response 2), ISAAC incoming 249→73(400,400)→81, and archived cache. 98 **sampled** region-readiness logs parsed. Last sampled result by offset:
- `-16,-16`: call 105, ready, 0 failures.
- `-16,48`: call 106, ready, 0 failures.
- `48,-16`: call 107, ready, 0 failures.
- `48,48`: call 160, NOT ready, 300 distinct failing object definition IDs within **that invocation**. Example IDs 83,85,114,179,196,202,205,255. This value is not a model-file count or final complete-scene count. Earlier 48,48 samples also returned ready, so readiness changes over time.

Real runtime still logs last observed detailed-scene blocker `-3` object-unwalkable; no observed `graphicsMode=2` promotion. New log only emits selected calls, so the last logged result is **not guaranteed to be the final actual invocation**. A true per-whole-scene snapshot (all offsets, same attempt) and model ID-to-object ID mapping remain needed; no playable world or Windows acceptance.

Private reproducible ZIP `SpawnPK_R261_Per_Call_Object_Readiness.zip` SHA256 `9e8164e5da39866724412ae1d62fb71a1066408602973d2c10b1b31754b62e04`; Java source, compile log, loopback replay, parser and summary. No original game binaries or credentials in package. Keep PR #1084 DRAFT.
