# R256 — actual source-built client gate instrumentation

Private TEMPORARY diagnostic source build on canonical R247 (1,277 Java files, `javac --release 11` pass), modifying only a diagnostic copy of `rs/Client.java` to throttle diagnostics in `tryEnableDetailedGraphics()`. Not a production-client patch. Authentic assets, isolated Xvfb test home, localhost-only 249/73/81 ISAAC packet replay.

## Root-cause discovery: region coordinate units
Prior R254/R255 probes passed `normal_region(3200,3200)`, incorrectly using **world tiles** as opcode 73 **8-tile chunk coordinates**. Client base calculation `(field856-6)*8` yielded `baseX=25552,baseY=25552`, no map/landscape file IDs were requested, and R256 gate initially returned `region-transition` (-4) with zero missing terrain/landscape and zero pending requests.

Changed only LOCAL TEST PROBE to `normal_region(400,400)`, corresponding to world tile neighborhood ~3200,3200. Client region base became `3152,3152`, requested real region cache IDs and reported:
- Early `R256_GATE gate=missing-terrain index=0 region=12593 mapId=254 landscapeId=255 terrainMissing=4 landscapeMissing=4 pending=8 graphics=1 base=3152,3152`
- Later `R256_GATE gate=objects-unwalkable ... terrainMissing=0 landscapeMissing=0 pending=392 graphics=1 base=3152,3152`.

This proves requested region terrain and landscape files **did become present** in the real client's in-memory arrays; an **object/walkability readiness check** then blocked detailed scene promotion. `pending=392` includes unrelated asset requests and does not establish 392 missing map files.

No stable terrain/player model rendered yet, no native Windows runtime, no source parity claim. Private evidence ZIP SHA256 `d6e29d833eac26ec408e7f579460dc456013297b98efc210068b0ee075de7603` contains redacted logs, diagnostic-only Client.java and probe, screenshot and compilation notes. Next inspect why `io_.areObjectsWalkable(...)` remains false (unresolved model prewarm vs invalid landscape bytes vs cache loader status) and prove readiness without fabricated map data. Keep PR #1084 DRAFT.